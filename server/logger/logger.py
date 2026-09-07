import logging 
import os 
from datetime import datetime

# Dynamic naming for log file 
LOG_FILE = f'{datetime.now().strftime("%m_%d_%Y_%H_%M_%S")}.log'
# Setting up Log File path 
logs_path = os.path.join(os.getcwd(),'server','logs',LOG_FILE)
# Even if there is a file and folder keep appending them in the folder
os.makedirs(logs_path,exist_ok=True)

LOG_FILE_PATH = os.path.join(logs_path,LOG_FILE)

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format='[ %(asctime)s ] - %(lineno)d %(name)s- %(levelname)s - %(message)s',
    level=logging.INFO
)
