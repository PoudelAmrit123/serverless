### Get the value from the reject and check if the rejection is large or not.
## the logic need to be changed mentining hte total value and selected and not selected.
## find the major part in ther error and pass that in the notification.


########## 

## After that get the value from the dynamodb and then analayse and give the notification.

## For that use of dynamoDB Stream and get that correlationID and using  the correlationID 
## get the value from the dynamoDB and send the notification accordingly.




# (######################################)
# (#######################################)


import json

def lambda_handler(event, context):
    print("Received EventBridge event:")
    print(json.dumps(event, indent=2))
    
    # Extract the correlation_id from the event detail
    correlation_id = event.get("detail", {}).get("correlation_id")
    
    if correlation_id:
        print(f"Correlation ID: {correlation_id}")
    else:
        print("No correlation ID found in the event detail.")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Notifier Lambda executed successfully",
            "correlation_id": correlation_id
        })
    }

