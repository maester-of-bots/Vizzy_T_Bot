import psycopg2
from datetime import *

from dotenv import load_dotenv
from modules.az_vault import *

import os

class db:
    def __init__(self, spam=False):

        self.vault = keyvault()

        self.server = self.vault.get_secret('PRD-DB-URL')
        self.user = self.vault.get_secret('PRD-DB-User')
        self.password = self.vault.get_secret('PRD-DB-Key')
        self.port = int(self.vault.get_secret('PRD-DB-Port'))
        self.database = self.vault.get_secret('PRD-DB-db')
        self.sslmode = self.vault.get_secret('PRD-DB-ssl')

        self.load_info(spam)

    def usage_dump(self, user_id, username, command, prompt, response, subreddit, link, cost, key_ref="Bean_12.23.22", columns=None, table="openai_usage"):
        """
        Dump OpenAI usage data to the cloud database server
        """

        # Columns is always None
        if columns is None:
            columns = ['user_id', 'username', 'timestamp', 'command', 'prompt', 'response', 'guild_id', 'channel_id', 'key_ref', 'cost']

        # Drop the data into the data list
        data = (user_id, username, str(datetime.now()), command, prompt, response, subreddit, link, key_ref, str(cost))



        conn = self.get_db()
        cur = conn.cursor()
        vals = ""
        for column in columns:
            vals += "%s, "

        columns = ", ".join(columns)

        vals = vals[0:-2]
        cur.execute(f"INSERT INTO {table} ({columns}) VALUES ({vals})", data )
        conn.commit()
        # Close communication with the database
        cur.close()
        conn.close()


    def get_db(self):
        # connect to MySQL server
        conn = psycopg2.connect(
            dbname=self.database,
            user=self.user,
            password=self.password,
            host=self.server,
            port=self.port,
            sslmode=self.sslmode)

        return conn


    def write_obj(self, obj_id, bot):
        self.comment_ids[bot].append(obj_id)
        conn = self.get_db()
        cur = conn.cursor()
        cur.execute(f"INSERT INTO reddit_bots (obj_id, bot) VALUES (%s, %s)", (obj_id, bot))
        conn.commit()
        cur.close()
        conn.close()

    def load_info(self, spam=False):
        if spam:
            bots = ['spam']
        else:
            bots = os.listdir('bots')

        self.comment_ids = {}

        for bot in bots:
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute(f"SELECT obj_id FROM reddit_bots WHERE bot LIKE '{bot}'")
            result = cur.fetchall()
            self.comment_ids[bot] = [x[0] for x in result]

        return True


    def check_db_direct(self, obj_id, bot):
        conn = self.get_db()
        cur = conn.cursor()
        cur.execute(f"SELECT obj_id FROM reddit_bots WHERE obj_id LIKE '{obj_id}' AND bot LIKE '{bot}'")
        result = cur.fetchone()

        cur.close()
        conn.close()

        # We haven't made this comment yet
        if result is None:
            return False

        # We already commented.
        else:
            return True


    def check_db(self, obj_id, bot):

        # We already commented.
        if obj_id in self.comment_ids[bot]:
            return True

        # We haven't made this comment yet
        else:
            return False


