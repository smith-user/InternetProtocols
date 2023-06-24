# Web Proxy

## Описание
Веб-прокси с поддержкой http и https.

Приложение выполняет функции web-proxy сервера.
В файл `./passwords/password.json` будут сохраняться 
учетные данные, введенные пользователями.

В логах можно видеть всю необходимую
информацию о работе приложения и возникающих ошибках.

## Требования
* Python версии не ниже 3.11

## Состав
* `common/` общий модуль, необходимый для работы программы 
* `proxy/` модуль прокси-сервера
* `features/` модуль дополнительных функций сервера
* `sslcert/` модуль, необходимый для создания TLS/SSL контекстов
* `tests/` тесты

## Запуск
```
python3 -m proxy
```

## Пример:
`python3 -m proxy --host 0.0.0.0 -p 8080`

## Инструкция:
Справка по запуску:
```
$ python3 -m proxy --help
usage: __main__.py [-h] [--host HOST] [-p PORT] [-u USERS] [-b BUFFER] [-t TIMEOUT]

Web-proxy

options:
  -h, --help            show this help message and exit
  --host HOST           Start proxy on host, default=localhost
  -p PORT, --port PORT  Start proxy on port, default=8080
  -u USERS, --users USERS
                        Set count of users, default=100
  -b BUFFER, --buffer BUFFER
                        Set buffer size, default=4096
  -t TIMEOUT, --timeout TIMEOUT
                        Set timeout wait request, default=1

```
