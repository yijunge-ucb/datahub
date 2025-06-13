### 
1. Create a new uptime checker and associate an alert policy with it for a namespace.
```
python3 create_alerts.py --create --namespaces dev-staging dev-prod

```
###
2. Enable an alert policy for a namespace.
```
python3 create_alerts.py --enable_alerts --namespaces dev-staging

```
###
3. Disable an alert policy for a namespace.
```       
python3 create_alerts.py --disable_alerts --namespaces dev-staging

```
