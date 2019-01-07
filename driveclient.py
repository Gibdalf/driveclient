from __future__ import print_function
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools
from magic import Magic
import io
import os

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/drive'
service = None


def connect():
    global service
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('drive', 'v3', http=creds.authorize(Http()))


# TODO: make this work with folders
# (currently only works with files in drive's root directory)
# TODO: test
def uploadFile(localPath, remoteName, parentId):
    """ Upload a single file to google drive.

    Arguments:
        localPath {string} -- path to the file to upload
        remoteName {string} -- path to the new file on drive
        parentName {string} -- name of parent folder on drive
    """
    mime = Magic(mime=True).from_file(localPath)
    file_metadata = {'name': remoteName,
                     'parents': [parentId],
                     'mimeType': mime}
    media = MediaFileUpload(localPath, mimetype=mime)
    file = service.files().create(body=file_metadata,
                                  media_body=media, fields='id').execute()
    print("Local file: %s, ID: %s" % (localPath, file.get('id')))


# TODO: make this work with folders
def downloadFile(remotePath, localPath):
    """ Download a single file from google drive

    Arguments:
        remotePath {string} -- path to the file on drive
        localPath {string} -- path to the new local file
    """
    fileId = findFileByName(remotePath)
    if fileId is None:
        return
    request = service.files().get_media(fileId=fileId)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))
    with open(localPath, 'wb') as f:
        f.write(fh.getvalue())


# TODO: make this work with folders
def findFileByName(fileName):
    page_token = None
    while True:
        response = service.files().list(q="name='" + fileName + "'",
                                        spaces='drive',
                                        fields='nextPageToken, files(id, name)',
                                        pageToken=page_token).execute()
        for file in response.get('files', []):
            print('Found file: %s (%s)' % (file.get('name'), file.get('id')))
            return file.get('id')
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    print("File not found")


# TODO: somehow differentiate between folders with same name
def createDriveFolder(name, parentId):
    file_metadata = {
        'name': name,
        'parents': [parentId],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = service.files().create(body=file_metadata,
                                  fields='id').execute()
    print('Folder name: %s, ID: %s' % (name, file.get('id')))
    return file.get('id')


def uploadFolder(localPath, parentId):
    name = os.path.basename(localPath)
    folderId = createDriveFolder(name, parentId)

    # recursive walk through directory
    # subdir is full path to current subdir
    # dirs / files are list of subdir's contents
    for subdir, dirs, files in os.walk(localPath):
        subName = os.path.basename(subdir)
        subId = findFileByName(subName)
        for dir in dirs:
            createDriveFolder(dir, subId)
        for file in files:
            uploadFile(subdir + "/" + file, file, subId)
    return


# TODO: implement
def sync():
    """ Syncronize all files in config file with google drive.
        If the remote version is newer, download it.
        If the local version is newer, upload it.
        Config file matches local files / folders to their remote equivalents.
    """
    return


if __name__ == '__main__':
    """uploadFile("arcticStars.jpg", "myBackground.jpg")
    downloadFile("myBackground.jpg", "myBackground.jpg")
    createDriveFolder("test", None)
    createDriveFolder("inner", "test")
    createDriveFolder("innerer", "inner")"""
    connect()
    uploadFolder("/home/alec/countdown", "root")
