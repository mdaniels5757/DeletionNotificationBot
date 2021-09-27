# DeletionNotificationBot

[User:Deletion Notification Bot - Wikimedia Commons](https://commons.wikimedia.org/wiki/User:Deletion_Notification_Bot)

This bot **notifies the uploaders** when their uploads get nominated for deletion and the **user who nominated the files for deletion did not notify the uploader**.

## Usage

```
git clone https://gitlab.com/Bd9a119b5d05019d7c923207398ef3c3/DeletionNotificationBot.git
cd DeletionNotificationBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
cp user-config.py.example user-config.py
openssl rand -base64 32 # PREFIX
openssl rand -base64 32 # KEY
vi config.yaml # 'prefix' and 'key' from output of above commands, 'pubfiledir' to any empty writeable folder
chmod 600 config.yaml Change the host to 'tools-redis.svc.eqiad.wmflabs' on toolforge.
vi user-config.py # Update the 'password_file' and run 'chmod 600 user-password.py'

```
## See Also
 - https://commons.wikimedia.org/wiki/Special:Contributions/Deletion_Notification_Bot
 - https://wikitech.wikimedia.org/wiki/Help:Toolforge/Redis_for_Toolforge
 - https://wikitech.wikimedia.org/wiki/Help:Toolforge/My_first_Pywikibot_tool
 - https://wikitech.wikimedia.org/wiki/Help:Toolforge/Pywikibot
 - https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams
 - https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern

***

## License
The MIT License

