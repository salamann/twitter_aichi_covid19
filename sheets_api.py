from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import pandas
import yaml

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

with open('settings.yaml', 'r', encoding="utf-8") as f:
    settings = yaml.safe_load(f)
    SPREADSHEET_ID = settings['SPREADSHEET_ID']


def get_auth():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def get_data_as_df(spreadsheet_name='by_city') -> pandas.DataFrame:
    return values_to_dataframe(get_data(spreadsheet_name=spreadsheet_name))


def values_to_dataframe(values: list) -> pandas.DataFrame:
    df = pandas.DataFrame(values)
    df = df.set_axis(df.loc[0, :], axis='columns').loc[1:, :].set_index('date')
    df.index = pandas.to_datetime(df.index)
    df = df.astype(int)
    return df


def update_values(values: list, spreadsheet_name='by_city'):
    """
    Creates the batch_update the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
        """
    try:
        row_number = len(get_data_as_df(spreadsheet_name=spreadsheet_name)) + 2

        service = build('sheets', 'v4', credentials=get_auth())
        body = {
            'values': [values]
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{spreadsheet_name}!A{row_number}:BD{row_number}",
            valueInputOption="USER_ENTERED", body=body).execute()
        print(f"{result.get('updatedCells')} cells updated.")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


def get_data(spreadsheet_name='by_city') -> list:
    try:
        service = build('sheets', 'v4', credentials=get_auth())

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=f'{spreadsheet_name}!A:BD').execute()
        return result.get('values', [])

    except HttpError as err:
        print(err)
    # return values_to_dataframe(get_data_as_df(creds))


if __name__ == '__main__':
    # creds = get_auth()
    # values = get_data(creds)
    # df = values_to_dataframe(values)
    # update_values(creds, len(values) + 1, [['123', '234', '345']])
    # creds = get_auth()
    values = get_data_as_df()
    # update_values(['123', '234', '345'], spreadsheet_name='by_generation')
    pass
