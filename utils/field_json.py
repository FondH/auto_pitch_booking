import pickle
import os
import pandas as pd
FIELDS_FILE = 'test_tmp_data/fields_data.json'

def save_field_info(field_info):

    with open(FIELDS_FILE, 'wb') as file:
        pickle.dump(field_info, file)

def load_field_info():
    if os.path.exists(FIELDS_FILE):
        with open(FIELDS_FILE, 'rb') as file:
            return pickle.load(file)
    return {}
