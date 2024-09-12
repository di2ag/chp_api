import os
import json
import requests

def zenodo_get(zenodo_id, file_key, file_type='infer'):
    """ This function will download the requested Zenodo file into memory.

    Args:
        :param zenodo_id: The string id for the Zenodo file. For example, if the Zenodo url is: https://zenodo.org/record/1184524#.ZD7aF_bML-g, 
            then the zenodo_id is: 1184524.
        :type zenodo_id: str
        :param file_key: This is a string to the file_key in the Zenodo bucket or in the zenodo record.
        :type file_key: string

    Kwargs:
        :param file_type: The file type of the hosted Zenodo file. If inferred, will try to infer type from file extension.
    """
    r = requests.get(f"https://zenodo.org/api/records/{zenodo_id}").json()
    files = {f[key]: f for f in r["files"]}
    f = files[file_key]
    download_link = f["links"]["self"]
    if file_type == 'infer':
        file_type = f["type"]
    if file_type == 'json':
        return requests.get(download_link).json()
    raise NotImplementedError(f'File type of: {ext} is not implemented.')

    

