# SMTP client

## Описание
SMTP клиент. В конфигурационном файле пользователь задает адрес получателя(лей), 
тему (возможно на русском языке) и имена файлов-аттачментов для отсылки в виде вложения.

## Запуск
```
python3 smtpclient.py -i client.ini
```

## Пример:

[Message.eml](https://github.com/smith-user/InternetProtocols/blob/main/smtp-client/example/Message.eml)

https://github.com/smith-user/InternetProtocols/assets/91221035/6aea87fc-cd25-4fe2-b779-e614ec98706e




## Инструкция:
Справка по запуску:
```
$ python3 smtpclient.py --help
usage: SMTP-Client [-h] [-i INI]

SMTP-Client with config.

optional arguments:
  -h, --help         show this help message and exit
  -i INI, --ini INI  config filepath.
```
