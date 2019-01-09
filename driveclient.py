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


def uploadFile(localPath, remoteName, parentId):
    """ Upload a single file to google drive.

    Arguments:
        localPath {string} -- path to the file to upload
        remoteName {string} -- path to the new file on drive
        parentName {string} -- name of parent folder on drive
    """
    fileId = findFileByNameAndParent(remoteName, parentId)
    mime = Magic(mime=True).from_file(localPath)
    media = MediaFileUpload(localPath, mimetype=mime)
    # specify id if the file already exists
    if fileId is None:
        createFile(localPath, remoteName, parentId, mime, media)
    else:
        updateFile(localPath, media, fileId)


def createFile(localPath, remoteName, parentId, mime, media):
    file_metadata = {'name': remoteName,
                     'mimeType': mime}
    if parentId is not None:
        file_metadata['parents'] = [parentId]
    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields='id').execute()
    print("Created drive file. Local file: %s, ID: %s" %
          (localPath, file.get('id')))


def updateFile(localPath, media, fileId):
    file = service.files().update(media_body=media,
                                  fileId=fileId,
                                  fields='id').execute()
    print("Updated drive file. Local file: %s, ID: %s" %
          (localPath, file.get('id')))


# TODO: make this work with folders
def downloadFile(remoteName, localPath, parentId):
    """ Download a single file from google drive

    Arguments:
        remotePath {string} -- path to the file on drive
        localPath {string} -- path to the new local file
    """
    fileId = findFileByNameAndParent(remoteName, parentId)
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


def findFileByNameAndParent(fileName, parentId):
    page_token = None
    query = "name = '" + fileName + "'"
    if parentId is not None:
        query += " and '" + parentId + "' in parents"
    while True:
        response = service.files().list(q=query,
                                        spaces='drive',
                                        fields='nextPageToken, files(id, name)',
                                        pageToken=page_token).execute()
        for file in response.get('files', []):
            return file.get('id')
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break


# TODO: somehow differentiate between folders with same name
def createDriveFolder(name, parentId):
    fileId = findFileByNameAndParent(name, parentId)
    if fileId is not None:
        print("found folder: " + name)
        return
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parentId is not None:
        file_metadata['parents'] = [parentId]
    file = service.files().create(body=file_metadata,
                                  fields='id').execute()
    print('Created drive folder. Name: %s, ID: %s' % (name, file.get('id')))
    return file.get('id')


def uploadFolder(localPath, parentId):
    name = os.path.basename(localPath)
    folderId = findFileByNameAndParent(name, parentId)
    if folderId is None:
        folderId = createDriveFolder(name, parentId)

    # recursive walk through directory
    # subdir is full path to current subdir
    # dirs / files are list of subdir's contents
    prevName = []
    prevId = []
    for subdir, dirs, files in os.walk(localPath):
        dirName = os.path.basename(subdir)
        parentName = os.path.basename(os.path.dirname(subdir))

        idx = -1
        dirParentId = parentId
        if parentName in prevName:
            # get the most recent occurence of parentName (in case of nested folders with same name)
            idx = max(loc for loc, val in enumerate(
                prevName) if val == parentName)
            dirParentId = prevId[idx]

        dirId = findFileByNameAndParent(dirName, dirParentId)
        prevName = prevName[:idx + 1] + [dirName]
        prevId = prevId[:idx + 1] + [dirId]

        print("subdir: " + subdir + ", prevname: " + str(prevName))

        for dir in dirs:
            createDriveFolder(dir, dirId)
        for file in files:
            uploadFile(subdir + "/" + file, file, dirId)
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
    # uploadFolder("/home/alec/Pictures/test", "root")
    uploadFolder("/home/alec/countdown", "root")
