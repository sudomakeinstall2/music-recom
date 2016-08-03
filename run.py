import logging
from logging.handlers import RotatingFileHandler

from app import app

handler = RotatingFileHandler('log.txt',maxBytes=100000,backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)

app.run(debug=True)
