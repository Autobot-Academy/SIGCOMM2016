from __future__ import print_function
import httplib2
import os
import codecs
from htmlentitydefs import codepoint2name

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

flags = tools.argparser.parse_args(args=[])

SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Sigcomm16'
SPREADSHEETID = '1AK4VdEuogGTaFRLia8Ef-AaZdAJOu5AxE7KAA1Nj7tU'

# spreadsheet headers
COL_TYPE = 0
COL_TIME = 1
COL_TITLE = 2
COL_CHAIR_SPKR_AUTHOR = 3
COL_KEYNT_ABSTRACT = 4
COL_SPKR_BIO = 5
COL_PHOTO_URL = 6
COL_FNAME = 7
COL_SLIDES = 8

# Borrowed from: https://www.safaribooksonline.com/library/view/python-cookbook-2nd/0596007973/ch01s24.html
def html_replace(exc):
    if isinstance(exc, (UnicodeEncodeError, UnicodeTranslateError)):
        s = [ u'&%s;' % codepoint2name[ord(c)]
                for c in exc.object[exc.start:exc.end] ]
        return ''.join(s), exc.end
    else:
        raise TypeError("can't handle %s" % exc.__name__)

codecs.register_error('html_replace', html_replace)

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-sigcomm16.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def proggen(worksheet, values, outdir):
    """
    TODO: could use some template engine here instead of just writing out the html/php .. 
    but the page is pretty simple, so this should do.
    """
    output = os.path.join(outdir, worksheet + '.php')
    print("Generating prog %s ..."%(output))

    f = codecs.open(output, mode='w', encoding='ascii', errors='html_replace')

    f.write("""<ul class="program" data-role="listview" data-filter="true" data-inset="true" data-theme="d" data-dividertheme="a" data-filter-placeholder="Filter program...">\n<?php\n""")
    for i,row in enumerate(values):
        if (len(row)<1):
            continue
        row = [item.strip() for item in row]
        line=None

        type = row[COL_TYPE]
        if (type == 'day' and len(row)>=2):
            line = """  tprog_add_header("%s");\n""" % row[COL_TIME]

        elif (type == 'session' and len(row)>=3):
            time = row[COL_TIME]
            title = row[COL_TITLE]
            chair = (row[COL_CHAIR_SPKR_AUTHOR] if len(row)>3 else "")
            style = ""
            if (i == len(values)-1):
                # last session
                line = """  tprog_add_session("%s", "%s", "%s", "%s", true);\n""" % (time, title, chair, style)
            else:
                line = """  tprog_add_session("%s", "%s", "%s", "%s");\n""" % (time, title, chair, style)

        elif (type == 'talk' and len(row)>=4):
            paper = row[COL_TITLE]
            link = ""
            authors = row[COL_CHAIR_SPKR_AUTHOR]
            info = ""
            slides = ""
            video = ""
            line = """  tprog_add_item("%s", "%s", "%s", "%s", "%s", "%s");\n""" % (paper, link, authors, info, slides, video)

        elif (type == 'keynote' and len(row)>=6):
            title = row[COL_TITLE]
            link = ""
            speaker = row[COL_CHAIR_SPKR_AUTHOR]
            abstract = row[COL_KEYNT_ABSTRACT]
            bio = row[COL_SPKR_BIO]
            photo = row[COL_PHOTO_URL]
            info = ""
            slides = ""
            video = ""
            line = """  tprog_add_keynote("%s", "%s", "%s", "%s", "%s");\n""" % (title, speaker, abstract, bio, photo)

        elif (type == 'disc' and len(row)>=3):
            paper = row[COL_TITLE]
            link = ""
            authors = ""
            info = ""
            slides = ""
            video = ""
            line = """  tprog_add_item("%s", "%s", "%s", "%s", "%s", "%s");\n""" % (paper, link, authors, info, slides, video)

        elif (type == 'break' and len(row)>=3):
            time = row[COL_TIME]
            title = row[COL_TITLE]
            line = """  tprog_add_session("%s", "%s", "", "");\n""" % (time, title)

        if (line != None):
            f.write(line)

    f.write("""?>\n</ul>\n""")
    f.close()

def main(outdir, wsnames):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    result = service.spreadsheets().get(
        spreadsheetId=SPREADSHEETID).execute()

    sheets = result.get('sheets', [])
    if len(sheets)==0:
        print('No worksheets found.')
    else:
        for ws in sheets:
            # do selected worksheets only
            if (len(wsnames)>0 and not ws['properties']['title'] in wsnames):
                continue

            # Note we assume the header row to be present !!!
            rangeName = '%s!A2:I'%ws['properties']['title']
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEETID, range=rangeName).execute()
            values = result.get('values', [])
            proggen(ws['properties']['title'], values, outdir)

    print("Done!")

if __name__ == '__main__':
    import sys
    if (len(sys.argv)<=1):
        print('Usage: python %s <outputdir> [worksheet names]'%sys.argv[0])  
        sys.exit(1)

    outdir = sys.argv[1]
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    main(outdir, sys.argv[2:])

