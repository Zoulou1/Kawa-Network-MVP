from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    details = response.data
    if isinstance(details, dict) and "detail" in details:
        message = str(details["detail"])
        fields = {}
    elif isinstance(details, dict):
        message = "Validation failed."
        fields = details
    else:
        message = "Request could not be processed."
        fields = {"non_field_errors": details}

    response.data = {
        "error": {
            "code": "validation_error" if response.status_code == 400 else "request_error",
            "message": message,
            "fields": fields,
        }
    }
    return response
