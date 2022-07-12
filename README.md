# LKML Gerrit Bridge

The LKML Gerrit Bridge attempts to provide a mechanism for getting changes and
reviews posted on LKML into Gerrit. The long term goal is to provide a
bidirectional bridge which allows a single review to be done in both LKML and
Gerrit. However, since the most difficult (and most useful) aspect of this
problem is to make LKML reviews visible in Gerrit we are starting there.

NOTE: This project is highly experimental and was mostly hacked together by one
programmer in his spare time as a hobby, so the code quality is not super great.
Sorry.

## What can the LKML Gerrit Bridge do now?

Right now, the Bridge will clone and periodically pull from the
https://lore.kernel.org/linux-kselftest/ git archives and push comments and new
patches to [this Gerrit
instance](https://linux-review.googlesource.com/q/project:linux%252Fkernel%252Fgit%252Ftorvalds%252Flinux).

## How do I set LKML Gerrit Bridge up?

You need to set up Gerrit cookies.

To set up a server which uploads emails sent to the kselftest email list, you
also need to build a docker image.

### Setting up Gerrit cookies

First you need to get Gerrit to generate an API cookie; you can do this by:

- Go to your Gerrit's setting page (e.g. https://linux-review.googlesource.com/settings)
- Scroll down to "HTTP Credentials"
- Click on "Obtain password"
- Follow the instructions to generate a `.gitcookies` file

Then you need to copy the cookies that were added to a file called
`gerritcookies` in this directory.

NOTE: YOU MUST ADD A COMMENT TO THE TOP OF THE COOKIE FILE: `# HTTP Cookie File`

### Setting up Google Cloud credentials

First you need to generate the gcloud credentials file. In order to do that,
you have to:

- Download gcloud CLI (follow instructions on https://cloud.google.com/sdk/docs/install)
- Run `gcloud auth appplication-default login` in the terminal

Then you need to copy the credentials file that was added to a file called 
`credentials.json` in this directory.

### Setting up Database information

Create a file named `.env` under `src/` that includes all of the following:

```
HOST = [HOST_NAME]
USER = [USER_NAME]
PASSWORD = [PASSWORD]
DB = [NAME_OF_DATABASE]

NOTE: The name of the database does not have to be an existing database.
```

### Building a docker image

First, make sure that you have Docker installed on the device which is building
the image. Before building, there are a couple of folders that should be
removed if you have run the server locally. Please run the following command
before building to ensure the image size isn't too large.
```bash
rm -rf linux_kselftest/ src/gerrit_git_dir/ src/index_files/
```

After ensuring these folders are deleted, you can build the image by running the
following command in the lkml-gerrit-bridge directory:
```bash
docker build -t myimage .
```
After running the build command, you will have created an image with the tag
'myimage'.

## Running LKML Gerrit Bridge locally

NOTE: You might not be able to actually push new changes to the Gerrit instace
unless your Git `user.name` has been granted the "Forge Committer" permission.

```bash
python3 src/main.py
```
