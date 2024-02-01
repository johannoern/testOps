import json

def lambda_handler(event, context):
   
    return {
        'statusCode': 200,
        'output': 'ok' 
    }

def entry_handler(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    return {
        'statusCode': 200,
        'output': 'ok' 
    }