import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

class keyvault:
    def __init__(self):

        self.name = "THC-Vault"
        self.uri = "https://THC-Vault.vault.azure.net"

        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.uri, credential=self.credential)


    def create_secret(self,sec_name,sec_value,sec_type):
        self.client.set_secret(sec_name, sec_value, content_type=sec_type)

    def get_secret(self, sec_name):
        retrieved_secret = self.client.get_secret(sec_name)
        return retrieved_secret.value

    def delete_secret(self,sec_name):
        poller = self.client.begin_delete_secret(sec_name)
        deleted_secret = poller.result()

