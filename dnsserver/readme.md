### DNS server

Кэширующий DNS сервер. Сервер прослушивает 53 порт. 
При первом запуске кэш пустой. 
Сервер получает от клиента рекурсивный запрос и выполняет
разрешение запроса. Получив ответ, сервер разбирает пакет ответа,
извлекает из него всю полезную информацию, 
т. е. все ресурсные записи, а не только то, о чем спрашивал клиент. 
Полученная информация сохраняется в кэше сервера.

**Usage:**
```
# python3 dnsserver.py --help
usage: dnsserver.py [-h] [--host HOST] [-s SERVER] [-c CACHE]

DNS server

options:
  -h, --help            show this help message and exit
  --host HOST           Start proxy on host, default=127.0.0.1
  -s SERVER, --server SERVER
                        DNS server address.
  -c CACHE, --cache CACHE
                        Cache filename, default=cache

```

