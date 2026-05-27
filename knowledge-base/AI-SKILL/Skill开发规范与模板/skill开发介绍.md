# skill开发介绍

> 来源: https://mi.feishu.cn/wiki/Vu1dwjOomiFUEgk3h55cbHd4noc

# skill 开发介绍

这里演示基于 antigravity + Opus 4.6 

1. 创建空文件夹

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NmJmM2Y3MzIyZjhhMWQ0YjZmOWM0MTg1YmYzNTBkOGVfNGJiOGIwY2JjY2JjM2FhMjQ5ZjQ1MjMyYTljM2VjOWJfSUQ6NzYyNDQwMzU1MDY5NzAzMjY2OF8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 打开IDE

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ODhkNTM1NTA4YjE2YjIwMjI5NTE4ZWRmZDU3YTY1MmNfYmY4Nzg2YWMwZTE1M2NlYWJkYjJiMzgzZDgwYzBkOGVfSUQ6NzYyNDQwMzU1MDA0NjkxNTc3NF8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 打开对应的文件夹（注意，这里方便调试，我直接把文件夹建在了 micode 的skills目录里）

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZWVmZjlhZTFjZDVmOWE4MmNjNWZjMDVlMTk1YWVhZThfZjM3OGJiODliMjdiNjk0MjhjYmNhZWJhZjA0NmI0ZTBfSUQ6NzYyNDQwMzU0ODY4NDMwNzQyMF8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 提需求

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=N2IxZWQ1ZmIwODNlN2I0N2I3NWM5NjNjN2YzYTYyMGFfMjM0YzBhMDIxODY0NmRiZjg1NDAyNzA1MjEwMDA0NjFfSUQ6NzYyNDQwMzU0ODgyNjU4NjI5MV8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGJlZjZhYWQzZmFhNDM4YzkyZDdiM2NmZDZlOTdkZGNfZTExZjYyYzg0ZjZjNTJlODFhZThjZThhMjJmOTU2MzBfSUQ6NzYyNDQwMzU1MDgwMDgyNTUzNF8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 添加reference（打开目录往里复制即可）

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDJjZDNhZTVlNmM4OWM0NzU3ZGJmYjg4NTYwYmRiODFfMDg4Njk4YTFkZmVlYTlhMjIxODhmZDIyYjEzZmMxNzVfSUQ6NzYyNDQwMzU0NzI5MTUxOTk2OF8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 调试

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2UwNDQ2MmE3MmYxNTU0MTk4NDhhZDIwNTkwNmU0ODVfODdiOTViNjI4YzY1NmQ1Nzc1YzY4N2UxYTYyNmM4ZjNfSUQ6NzYyNDQwMzU1MTM2MzU1MDQyN18xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 打包

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDhiY2Y3NzI3MzAyYWVhMjhkN2IyNGYxYWJkYzk1MDJfYWViNzcxOTRmOTVjMjFkYTVjZWViOTFlNWU1MjIzNjVfSUQ6NzYyNDQwMzU0ODgyNjQyMjQ1N18xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)



1. 上传

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzNjMjExYmI3NWI4NjIyNmM3YTE1OWMxMTExYTExZGFfOTU0Mjc5NzJmNDBjMGMyYzhlM2VjNTIyYTlkZTY0YmJfSUQ6NzYyNDQwMzU0OTMyMTE2OTg4NV8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=N2M0NTM3NDA0NGY3YzM3M2UwMTA5MGM5ZTc0NDg1NTZfMjBhMTg2YjkzZGM4YzEyYTg0MzkwZjBhOWUxMTkzYmRfSUQ6NzYyNDQwMzU0ODY2MzEwNjc4Ml8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)

1. 查看

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=M2NlNzQ0NWNjMGI5OWJmYWM4ZDUwNTFhZGU4OGE4MGZfMWIwMjk5ZTViYzEzYzQ4ODUzN2ZhM2EyMWRmOWI3OGFfSUQ6NzYyNDQwMzU1MDQ4MzAwODczNl8xNzc5ODcxNDAzOjE3Nzk4NzUwMDNfVjM)