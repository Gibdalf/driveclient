# Progress

## What Works
- upload files to drive
    - specify local path, remote name, remote parent id
    - if the file already exists, update the file
    - else, create a new file
    - all files in drive made by this program will not have the same name and parent
- create files in drive
    - specify local path, remote name, remote parent id
- update existing files in drive
    - specify local path, remote id
- upload folder to drive
    - create folder in drive for base dir
    - recursively upload subdirectories, and upload files, so that they maintain the same directory heirarchy
- download files from drive
    - specify local path, remote name, remote parent id
- create drive folder
    - create based on name and parent id
    - if there is already an existing folder with the same name / parent, don't make a new one
    - all folders in drive made by this program will not have the same name and parent

## What Needs To Be Done
- download full folder from drive
- compare local and remote file (find which is newer)
- full sync
    - read config file
    - for each file / dir listed, compare local with remote.
        - if remote doesn't exist, upload local
        - if local newer than remote, upload local
        - if remote newer than local, download remote
    - how to handle if local doesn't exist:
        - if remote exists (exists file / folder with same basename as suggested file path), download remote, create local file / dir
        - if remote doesn't exist, do nothing (log to stderr?)
