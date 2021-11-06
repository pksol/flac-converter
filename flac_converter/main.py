import glob
import os
import shutil

import cloudconvert


class CloudConvertError(Exception):
    def __init__(self, message, failed_task):
        super().__init__(message)

        self.failed_task = failed_task


def wait_and_raise(task_id, operation):
    """
    Waits till the task is complete and verify its status.

    Any other status than 'finished' would raise an error with the information

    Args:
        task_id: the task to check
        operation: the logical operation - would be used in the exception

    Returns:
        dict - the successful task

    Raises:
        CloudConvertError - for failed task
    """
    task = cloudconvert.Task.wait(id=task_id)
    if not task['status'] == 'finished':
        raise CloudConvertError(
            f"Failed to {operation}: {task['message']} - {task['code']}", task)
    return task


def convert_file_to_mp3(file):
    job = cloudconvert.Job.create(payload={
        'tasks': {
            'upload-my-file': {
                'operation': 'import/upload'
            },
            'convert-my-file': {
                'operation': 'convert',
                'input': 'upload-my-file',
                'output_format': 'mp3',
            },
            'export-my-file': {
                'operation': 'export/url',
                'input': 'convert-my-file'
            }
        }
    })

    print(f"uploading {file}, this can take a while")
    upload_task_id = job['tasks'][0]['id']
    upload_task = cloudconvert.Task.find(id=upload_task_id)
    cloudconvert.Task.upload(file_name=file, task=upload_task)
    wait_and_raise(upload_task_id, "upload file")

    print(f"waiting for {file} convert, this can take a while")
    convert_task_id = job['tasks'][1]['id']
    wait_and_raise(convert_task_id, "convert file")

    print(f"waiting for {file} download, this can take a while")
    exported_url_task_id = job['tasks'][2]['id']
    download = wait_and_raise(exported_url_task_id, "get download file link")

    print(f"downloading {file}, this can take a while")
    converted_file = download.get("result").get("files")[0]
    downloaded = cloudconvert.download(filename=converted_file['filename'],
                                       url=converted_file['url'])

    shutil.move(os.path.join(os.getcwd(), downloaded),
                os.path.splitext(file)[0] + ".mp3")


def main(file_selector):
    sandbox = os.getenv("USE_SANDBOX", 'False').lower() in ('true', '1', 't')
    cloudconvert.configure(api_key=os.environ['API_KEY'], sandbox=sandbox)

    for file in glob.glob(file_selector):
        # save credits - convert only the unique files
        if not os.path.isfile(os.path.splitext(file)[0] + ".mp3"):
            convert_file_to_mp3(file)


if __name__ == '__main__':
    main('/mnt/e/CarMusic/*.flac')
