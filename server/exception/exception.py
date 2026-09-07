# Sys module helps us make changes in the python runtime enviroment and helps us get all the error details occured in the project
import sys
from server.logger.logger import logging
# Creating a resuable function that fetches error details from the sys module and prints a custom error message 
def error_message_details(error, error_detail: sys):
    # If error_detail has exc_info, extract traceback
    exc_info = error_detail.exc_info()
    if exc_info[2] is not None:  # means an actual exception occurred
        _, _, exc_tb = exc_info
        file_name = exc_tb.tb_frame.f_code.co_filename
        error_message = (
            f"Error occurred in python script name [{file_name}], "
            f"line number [{exc_tb.tb_lineno}], "
            f"error message [{str(error)}]"
        )
        return error_message
    else:
        # No actual exception, just return the string
        return str(error)

# Creating custom error class 
class CustomException(Exception):
    def __init__(self,error_message,error_detail:sys):
        super().__init__(error_message)
        self.error_message = error_message_details(error_message,error_detail=error_detail)
        
    def __str__(self):
        return self.error_message
    
if __name__=='__main__':
    try:
        a = 4/0 
        print(a)
    except Exception as e:
        logging.info(CustomException(e,sys))
        raise CustomException(e,sys)
    