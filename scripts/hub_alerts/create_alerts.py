import subprocess
import json
import re
import yaml
import argparse




def find_target_channels(namespace, project_id):
    target_channels = []
    if "staging" in namespace:
        target_channels.append(project_id + "-staging-alert-channel")
    if "prod" in namespace:
        target_channels.append(project_id + "-prod-alert-channel")
        target_channels.append("Berkeley Datahub - PagerDuty")
        target_channels.append("ds-infrastructure-email")
    return target_channels


def extract_channel_names(target_channels):
    try:
        result = subprocess.run(
            ['gcloud', 'alpha', 'monitoring', 'channels', 'list'], 
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running gcloud command: {e}")
        return None
    
    yaml_content = result.stdout
    documents = yaml.safe_load_all(yaml_content)
    
    channel_names = []
    for document in documents:
        if document.get('displayName') in target_channels:
            channel_names.append(document.get('name'))
    
    return channel_names



def get_notification_channels(namespace, project_id):
    target_channels = find_target_channels(namespace, project_id)
    notification_channels = extract_channel_names(target_channels)
    return notification_channels
    
    

def create_uptime_check(namespace, domain, project_id):
    """
    Function to create the uptime check and capture the uptime_check_id
    """
    if "staging" in namespace:
        host = namespace + "." + domain
    elif "prod" in namespace:
        host = namespace.split('-')[0] + "." + domain
    else:
        print(f"Could not create uptime check for {host}. ")
        return None
    # Run the uptime check creation command
    command = [
        "gcloud", "monitoring", "uptime", "create", f"{namespace}.{domain}",
        "--resource-labels", f"host={host},project_id={project_id}",
        "--resource-type", "uptime-url",
        "--request-method", "get",
        "--validate-ssl", "true",
        "--protocol", "https",
        "--port", "443",
        "--status-classes", "2xx",
        "--period", "1",
        "--timeout", "10"
    ]
    
    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error creating uptime check for {namespace}.{domain}. ")
        return None
    
   
    # The expected output format is: "Created uptime [projects/<project_id>/uptimeCheckConfigs/<uptime_check_id>]."
    uptime_check_id_match = re.search(r"Created uptime \[projects/[^/]+/uptimeCheckConfigs/([^/]+)\]", result.stderr)
    if uptime_check_id_match:
        return uptime_check_id_match.group(1)
    else:
        print(f"Could not extract uptime_check_id for {namespace}.{domain}")
        return None




# Iterate through each namespace and domain to create and run the `gcloud` command

def create_alerts(namespaces, domain, project_id):
    for namespace in namespaces:
        notification_channels = get_notification_channels(namespace, project_id)
        if not len(notification_channels):
            print(f"Could not find a notification channel for {namespace}. ")
            continue
        
        # Create uptime check and capture uptime_check_id
        print(f"Creating uptime check for {namespace}.{domain}...")
        uptime_check_id = create_uptime_check(namespace, domain, project_id)
    
        
        if uptime_check_id is None:
            print(f"Skipping alert policy creation for {namespace}.{domain} due to uptime check creation failure.")
            continue
        
        duration = "600s"
        if "staging" in namespace:
            duration = "1800s"
            
        # Create JSON structure for alert policy
        alert_policy = {
            "displayName": f"{namespace} uptime failure",
            "conditions": [
                {
                    "displayName": f"{namespace} uptime failure greater than 1",
                    "conditionThreshold": {
                        "aggregations": [
                            {
                                "alignmentPeriod": "600s",
                                "crossSeriesReducer": "REDUCE_COUNT_FALSE",
                                "groupByFields": [
                                    "resource.label.project_id",
                                    "resource.label.host"
                                ],
                                "perSeriesAligner": "ALIGN_NEXT_OLDER"
                            }
                        ],
                        "comparison": "COMPARISON_GT",
                        "duration": duration,
                        "filter": f"resource.type = \"uptime_url\" AND metric.type = \"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.labels.check_id = \"{uptime_check_id}\"",
                        "thresholdValue": 1,
                        "trigger": {
                            "count": 1
                        }
                    }
                }
            ],
            "alertStrategy": {},
            "combiner": "OR",
            "enabled": True,
            "notificationChannels": notification_channels,
            "severity": "CRITICAL"
        }
        
        # Write the alert policy to a JSON file
        json_filename = f"{namespace}_{domain}_alert.json"
        with open(json_filename, 'w') as f:
            json.dump(alert_policy, f, indent=2)
        
        # Run the gcloud command to create the alert policy
        try:
            print(f"Creating alert policy for {namespace}.{domain}...")
            command = [
                "gcloud", "alpha", "monitoring", "policies", "create",
                f"--policy-from-file={json_filename}"
            ]
            subprocess.run(command, check=True)
            print(f"Alert policy for {namespace}.{domain} created successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error creating alert policy for {namespace}.{domain}: {e}")


def main():

    parser = argparse.ArgumentParser(description="Create alerts with specified parameters.")
    
    parser.add_argument('--namespaces', help="Comma-separated list of namespaces.", nargs="*")
    parser.add_argument('--domain', help="The domain to use for alerts.", default="datahub.berkeley.edu")
    parser.add_argument('--project_id', help="The Google Cloud project ID.", default="ucb-datahub-2018")
    
    args = parser.parse_args()
    
    create_alerts(args.namespaces, args.domain, args.project_id)
    


if __name__ == "__main__":
    main()