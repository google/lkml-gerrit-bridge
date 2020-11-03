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

Not a whole lot. It can pull in patches from a Gmail account, extract comments,
map those comments into where Gerrit expects them, and provides some Python
wrappers around Gerrit.

## How do I set LKML Gerrit Bridge up?

You need to do two things: Set up Gmail, and set up Gerrit cookies.

To set up a server which uploads emails sent to the kselftest email list, you
need to set up Gerrit Cookies and build a docker image.

### Setting up Gmail

First you need to create a label in your Gmail account called "KUnit Patchset".
You need to then attach this label to any email you might want to import as a
pach into Gerrit.

Next you need to get a `credentials.json` file which will tell the LKML Gerrit
Bridge what your Gmail account is and stuff like that. You can get that here:
https://developers.google.com/gmail/api/quickstart/python#step_1_turn_on_the

Finally, you need an API token. You can get that simply by running the
patch\_parser. You can do this by running:

```bash
python3 patch_parser.py
```

NOTE: PYTHON MUST BE ABLE TO OPEN A BROWSER WINDOW FOR THIS TO WORK!!!

### Setting up Gerrit cookies

First you need to get Gerrit to generate an API cookie; you can do this by:

- Going to your Gerrit's webpage
- Clicking on "Generate Password"
- Following the instructions to generate a `.gitcookies` file

Then you need to copy the cookies that were added to a file called
`gerritcookies` in this directory.

NOTE: YOU MUST ADD A COMMENT TO THE TOP OF THE COOKIE FILE: `# HTTP Cookie File`

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

## Using LKML Gerrit Bridge

Right now all the LKML Gerrit Bridge does is find patches under you Gmail label
and extracts comments. You can do this by running:

```bash
python3 patch_parser.py
```

## Eratta

- Right now we have the patches it is looking for hardcoded, but we will be
  fixing that shortly.
- LKML Gerrit Bridge currently only works with Gmail. Again, we will be fixing
  that shortly.
- LKML Gerrit Bridge does not actually upload patches to Gerrit. We will be
  fixing this shortly.

