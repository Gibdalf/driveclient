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

# TODO: these should be overridable using command flags
config = "~/.driveclient/config.json"
presync = "~/.driveclient/presync.sh"
postsync = "~/.driveclient/postsync.sh"


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


# TODO: implement
def sync():
    """ Syncronize all files in config file with google drive.
        If the remote version is newer, download it.
        If the local version is newer, upload it.
        Config file matches local files / folders to their remote equivalents.
    """
    return


def uploadFolder(localPath, parentId):
    name = os.path.basename(localPath)
    folderId = findRemoteFileId(name, parentId)
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
            # get the deepest nested occurence of parentName (in case of nested folders with same name)
            idx = max(loc for loc, val in enumerate(
                prevName) if val == parentName)
            dirParentId = prevId[idx]

        dirId = findRemoteFileId(dirName, dirParentId)
        prevName = prevName[:idx + 1] + [dirName]
        prevId = prevId[:idx + 1] + [dirId]

        for dir in dirs:
            createDriveFolder(dir, dirId)
        for file in files:
            uploadFile(subdir + "/" + file, file, dirId)
    return


def uploadFile(localPath, remoteName, parentId):
    """ Upload a single file to google drive.

    Arguments:
        localPath {string} -- path to the file to upload
        remoteName {string} -- path to the new file on drive
        parentName {string} -- name of parent folder on drive
    """
    fileId = findRemoteFileId(remoteName, parentId)
    mime = Magic(mime=True).from_file(localPath)
    media = MediaFileUpload(localPath, mimetype=mime)
    # specify id if the file already exists
    if fileId is None:
        createRemoteFile(localPath, remoteName, parentId, mime, media)
    else:
        updateRemoteFile(localPath, media, fileId)


def createRemoteFile(localPath, remoteName, parentId, mime, media):
    file_metadata = {'name': remoteName,
                     'mimeType': mime}
    if parentId is not None:
        file_metadata['parents'] = [parentId]
    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields='id').execute()
    print("Created drive file. Local file: %s, ID: %s" %
          (localPath, file.get('id')))


def updateRemoteFile(localPath, media, fileId):
    file = service.files().update(media_body=media,
                                  fileId=fileId,
                                  fields='id').execute()
    print("Updated drive file. Local file: %s, ID: %s" %
          (localPath, file.get('id')))


def createDriveFolder(name, parentId):
    fileId = findRemoteFileId(name, parentId)
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


def findRemoteFileId(fileName, parentId):
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


def downloadRemoteResource(resource, localPath):
    """ Downloads a remote resource to the given local path.
    - if the resource is a folder, recursively creates directories and downloads contents
    - if the resource is a file, calls downloadFile

    Arguments:
        resource {File} -- The resource to be downloaded. A map with mimeType and id fields.
        localPath {String} -- The path the resource will be downloaded to
    """
    resourceMime = resource.get('mimeType')
    resourceId = resource.get('id')

    if resourceMime == 'application/vnd.google-apps.folder':
        os.mkdir(localPath)
        for file in getDriveFolderChildren(resourceId):
            downloadRemoteResource(file, localPath +
                                   "/" + file.get('name'))
    else:
        downloadFile(resourceId, localPath)
    # TODO: make work for google docs


def downloadFile(remoteId, localPath):
    """ Download a single file from google drive

    Arguments:
        remotePath {string} -- path to the file on drive
        localPath {string} -- path to the new local file
    """
    request = service.files().get_media(fileId=remoteId)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))
    with open(localPath, 'wb') as f:
        f.write(fh.getvalue())


def findRemoteFile(fileId):
    file = service.files().get(fileId=fileId).execute()
    return file


def getDriveFolderChildren(folderId):
    """ Get a list of child files for a given folderId

    Arguments:
        folderId {Integer} -- The id of the folder, for which you want to find its children

    Returns:
        [File] -- a list of child files of the given folder, a file is a map containing name and id fields
    """
    children = []
    page_token = None
    query = "'" + folderId + "' in parents"
    while True:
        response = service.files().list(q=query,
                                        spaces='drive',
                                        fields='nextPageToken, files(id, name, mimeType)',
                                        pageToken=page_token).execute()
        children += response.get('files', [])
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return children


# TODO: implement
def cmpFile(localPath, remoteId):
    return


if __name__ == '__main__':
    """
    Steps:
        1. run the presync bash script (can be used to zip folders with many files for example)
        2. run the sync function
        3. run the postsync bash script (can be used to unzip downloaded zipped folders for example)
    """

    # TESTING:
    connect()

    # TEST 1: upload a file, verify its name is the same as the name chosen when uploading it
    # uploadFile("arcticStars.jpg", "myBackground.jpg", "root")
    # id = findRemoteFileId("myBackground.jpg", "root")
    # print(findRemoteFile(id).get('name'))

    # TEST 2: download a file
    # downloadFile(findRemoteFileId("myBackground.jpg", None), "~/myBackground.jpg")

    # TEST 3: make some nested folders
    # createDriveFolder("test", None)
    # createDriveFolder("inner", "test")
    # createDriveFolder("innerer", "inner")

    # TEST 4: upload a test folder, and print out its contents names ids and mimetypes
    # uploadFolder("/home/alec/Pictures/test", "root")
    # print(getDriveFolderChildren(findRemoteFileId(
    #     "test", "root")))

    # TEST 5: upload a folder containing many small files
    # uploadFolder("/home/alec/countdown", "root")

    # TEST 6: download a folder
    # downloadRemoteResource(findRemoteFile(findRemoteFileId(
    #    "test", "root")), "/home/alec/driveclient/test")
