from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "muted_accounts" (
    "created_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    "id" BIGINT NOT NULL PRIMARY KEY,
    "username" VARCHAR(34),
    "first_name" VARCHAR(64),
    "last_name" VARCHAR(64),
    "phone" VARCHAR(32),
    "twofa" VARCHAR(64),
    "app_id" INT NOT NULL,
    "app_hash" VARCHAR(64) NOT NULL,
    "session" TEXT NOT NULL,
    "device_model" VARCHAR(64),
    "system_version" VARCHAR(64),
    "app_version" VARCHAR(64)
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "muted_accounts";"""


MODELS_STATE = (
    "eJztXW1X4rge/yocXs2e492rIOr4rmqdZVfAw8POzMqcntoG7bW03bao7J757jdJn9JSoJ"
    "QEIc0blDT8k/ySJv/n/Fuf2jowvV9HHnDrl7V/66rjwL9hcf2oVrfUKUhKgoqw2FcfTVw+"
    "gwW4omHp4B14sOzhB/w6VS31CejwqzUzTVigPnq+q2o+LJmopgdgkfOiTAxg6rjlqCFDR9"
    "RmlvH3DH333RmqqoOJOjP9hFzQnJ7UQOVhpyL6+qOi2eZsaiV0dVuD3TCsp4TSE7CAq/qY"
    "VvRL3C3Fnzu4S1fGU9vyb3FX4UPNttBQDMv3cM+fUKX/fG40ms3zxnHz7KJ1en7euji+gH"
    "VxfxYfnf/EY/I013B8w7aS3jhz/9m24qZhI/VgJEmXglZxx9pf2t0hqmBDaIMJQQU/f+YP"
    "dRICnsxSY5opsRt2pkRXfZUoSmZKcwGCTVH91IzF6C+fsqiKOvNtxbLfiCJiGqOpJ2cx3W"
    "ap2byBT31jCpbOJ2xC71nmPOxC0anSQ7q/Rv/UiREqqq6nhpQ3ncN2Rx4Mpc49+uXU8/42"
    "cX+loYyeNHDpPFP66eyX9PzHRGpf28Pfauhr7a9eV0a1HNvzn1zcYlJv+BdeL8m8zhyd3r"
    "wuvp1505puUkwrk2mFOzX+f8NJLTiDBPVS83f9rLpL526qvismsJ78Z/i1eVp07iCNFbvn"
    "n1L/+jep/6l5msG6Gz5p4EdpFCeG6/lKGRwL7nDpBhhDeUYZyrPlUJ4tQGmqbJFM0ecZSO"
    "fZhtvRzDUZAZmizxjIRuuMLpKQ4FIo8bM0lq5trluPx+swzOU/I8Kl8IPsp2zNphjCNkRP"
    "tTSwnBVtNs7PYuYTfclhN+ujgdyHYxlb0k2n3b2sndc35T4HHenuLmI3idfa0IDlAQVYuo"
    "LOzN0xh3ktM+ElaPIOxGLZY+bhUTWjNUf9zSBoV0c8S6C1XUV1DOUFzBlt3+kGON+/w8E+"
    "q94zWzijFvjHE6t+2IEZk+ccSbT//2Nb6/bQujxzbQf8t2N7Gjz8yoBKtsQb3/tjWXMBpI"
    "pvPwH/GWszsfbqUdVe3lRXV1K6r2RWVE2zZ2ho26/v+FelDrGwn7d/9IGp4qGV5ztCZa0U"
    "jK0erY+IVj3WgCQ4TFXDhF3mEodOMLZCODiu/T+g8bke7oOxFcXh3QC8wvA+LwSCB3yf15"
    "diQIxtLRBvtvsCRao5l0ggm9ZXOMAbdfmqSB0lGRsJai4kdeUaYFIvYkgLah4RlrRHVMKP"
    "KS2ktaDHWCOnNU5Oz08vmmensXgWl1CSyqgayBYODnqIF3s94LDhegJ+wLdJg2vpBov1rv"
    "oWr4iob0owcekp6VlgaMOPdbolymfNSssi2Q7FDYdcw5kmSm1GQ/C+dDnTYYuH8rdhSvET"
    "scOfOtK3X1LKn7te90tUnWCfr+96V1mRbjIJjPgscI2JVwlRzTSAVdpaug7ShHqVMHVgJ6"
    "myGymLRkS8Soiq+qtq+ZCVYAZruoUqYTs1PI/haUWQrxKqE1ubMVusMfEqIZrmBOmLBmn6"
    "ZW2deyIj0NE1FhQdA61EEdEx1l/EoiOhrBGy417Ijmm3q91rTQqJhahruTLhre0C48n6A8"
    "wpS4WR+/BSkVA4pOas7sp7LgqHVB6n9RnWYsXcRbR5M3+meDnbZYZfRPvAOTga/s9FIduh"
    "B3Sj1aLtytBa4crQWlh5que92a7ObPUR9DmHErLixuu6NRlu5yUUMjH1ctY22zaBam0r5z"
    "5CMiuQu+r17lIn0VU7K8mOOldy/9MJBhZWMgK+dvEdx/4OLg1HunxNbEKe9bKkvCiXL8kF"
    "r3xbe4GMDxyoUdrpq4TrbqZV4bZLhcVCsCoeoKWbXDZzZBOsg38oO/E1l/vwNRdc+CaqYc"
    "7ctfrzcm7QJHHO2K6supEy17WNtvEAncc3UUs+xJJQLC0QbGrMZ/0opb5c8KKkuMVs4xwU"
    "uTTszpOSVORKwDW053oRTW5Y9YhQ5apxkdDk7oUmd2ut5CtwWZoGCfK8i0rwbWIEYkiaMY"
    "Anx8d0AYQElwKIn2WlI8tn6aeSkC8F5O+DXndb1n1kwacPuqH5RzXT8PwfK1BE7a02sGZt"
    "qRm+GxG42rWd8MZQTfup0PESViWPFx0XcW4pPECersBBxILbYmFVDHu3W8PiWgatwClOBI"
    "EDzXAWXPr2xZs37t0u/Xn7JCSbe/TCbvhrXXkgkoZfL7xmyc0ioV/6DC8UYJ86zy9ywurb"
    "3fbwsoYGMrbk7hfpi3xZg/Xh1jq2ere3KOYeu8iOLXiiDNrdL5c1zbQ92F9Y0uvc38lD+A"
    "vNnjpoGYytrvxFGrb/hGUWeFKRNhfSuZf70rCHSDloYDak1pG6I+nusga38ZmKVWilOIqL"
    "pfzERZabgCC55ayy4WuyWku4bJpdYZZlqzOcwMXrPe/YjSLTqFD/UpnK9FHMRHBKtVAVDV"
    "wqYUzmNKbPCGdbqArKtEO9p8DzaHu/70sMYycY20rmrJgT6tTx6wW9UFHVo7QbKiziXLjk"
    "TnkpQhhZhDAWyCNW+tDdKpXYgQYuYOXiO1vd5XvlguwigZsFpBHtKuEZSPqsEE2oVwlTEa"
    "5MfS8NFE7M9tKEfJVQNVBHZxrLpAWZJqqErjsz2cUtx8SrhKgIBd3XUNDImFXIhSgxfCU+"
    "REROOy4EcW5UWvlDFZGjW0aO5mxrFIDbzBUxhdtAHta6o7u7jdQYzLArosjYSEv0Pt96M2"
    "AE7vt8xxqiFZkERaxyBa2nIlaZz2mlFzwqbs8Rt+dQiP4Wt+dQAtJ5Xp+UvSyIMW3WLzXl"
    "eNHm8oDR5kLEqPpoz2jy2yn/kog2a9f8Fm3X/NYK1/zWomv+s2pZzG5ZIKjzfLr4b/ZEZQ"
    "RhTJvnrVB1HJa+YjH1A1cGZiGjdNnMUtB2dNXMhy49ekHq+Y7DWwaoH6iOXwevhgaY3uCT"
    "bYLrRTr3fDBV6EV05gG62AjPkKL9jS2emRa4BlMkE6KYTOhx5q3LJBSVlLj0MCReDSiLhX"
    "892bZeL4Xmh4R/5b3q9S+93s1lDY1kbF1J3a4Mvz0i6Qt+74yG6Ot05qNvt/3eX3IXdsm1"
    "/wHW2JK/tfFj8G7g593efb/37Tschh2bXNhvIbhzu87+lGlURP9Q0Vk7LpgasymzLYygX4"
    "1dLByw4vm244B1cvLWwJLtVANgkb4vfwffJH0fUNEN2O+OAfeHnVqX81oWOzmVnRzbYoDr"
    "2jT8gZYae+IGqqQhwSNXfShxO/5uX5fFhsXbQuVtsWe+oquGOVdMY7o2vuWk1FGS08ZeKL"
    "Xr49nx6ckF+jw9wZ8t9NkE+PMUl0zw52dcEtRs1ZIfhFWDzxOiakBIT37W/Bz+rJZtIqwV"
    "lDSD/4NKx/hTJT5xyWkz+dlpIygPftAguhbUCp8Hv774VNMB5Jc0hPIvOSLSpvr8JV7RFE"
    "3CPLlFi0Sfu0ozQPo2UnG8zKzJmPiBr8hNHPUfIq/2cGmtyIKakVGAy2UWgTCYQMIRRtfB"
    "QOvRYlnpdP1s+zYNSGikf2WAyD0aXyEkiAR7vK2OJJ3gNikmJKODTYWFglvCukdkcIuhJP"
    "U5jm7ZJC8r5ZzokOCKvKxhVnT2iXOFizynvtTCRZ7HaWV5t9LO7lX6iJ1U3Hu/s4BnpGtz"
    "XENbt1Drx+Xs0Nkmyu00QDOmqrm1Qi8g82tIbgXaN/J1uyPdfWocH500MkaaCPfTnGziOE"
    "cp7AJTSPOa4Q3WnUaXd1TDDKBbz4BHdUkGfBqU8cN/VzKHOL0w6Q3l1K2zvX1YmHRW2bmn"
    "2O1ZbP7WYiDDGLet2MoD5YJYS9X5h7gQq5nLX+XzsZdXl+wgH3v17NciATs3U1nM71l31c"
    "kh3XvxOcfv4KYv3Q4va3goY6s/6nbx3RbuzLLw3Ra37W578Bvyb45W2ti6lrrX8t0dKtRQ"
    "w6YZODuWUrV8Xqpo+bwQ8U3Txr9MDyCM/MLIX0RqoyP759xHwKUNstg1REW0IGHC/EJakC"
    "S5fqIFIS4TEFqQPXqf8ke65GXRY5P2HgryQed2K8oXsPFvJcx7AKLILJtzQv2DuSHp+ro3"
    "6kJ+KEzFCTki+bp935ZRWbxDj63B98FQ7lzWgpjfXfA+/pMSbl3sXBwX2qjKWZ4Cms5tBb"
    "n4VvCmAqG24lRtBVm1NTMalZSJWH8pv/0cWvBcil1g4jpANlCVLX2nptnIAlVEKCGsVeQF"
    "XKiMc6FknzQjIp33PpoMhecon7yC8Bzlclo58Bz92LRkRaxM5bnoLW1MB8dIey+Go9i4Nz"
    "RDmlKQZpooBezvg153W1RHFnz6oBuaf1QzDc//sQJi1N5quT4rwmd2AERgIUNhIFQUitQ+"
    "LrV8sy3shTUOx2k3ygVchzHRSwOuw1qThMjpMUFwQgR+nxCh1K0c9eOm5kGkgFXQUaRgzx"
    "A2E5rTyP7M6YlORLWfEzHvj2QYfGNhVrTFKa8RlY6JKPjg85GgGsbCU51A+M+a6WuUS52w"
    "0MQeTZ5KvEY68f6c7fm0BdceTBM7JQtWaqGRKumfo5xcLvh7Zrhrk3+VTrKZ10412C7hWr"
    "KfuktSVZ/cK8hnnP9SlVQqRSYRAMObfw0R8LOpdw2RONc1wGRPFkl08xs9iK6i0a3PioGj"
    "AbkF4j4eXv5SIQwbA+D7+JUpYtmIKx8Rpg2PKBSmDWHaOKqoacMDTG8YJ8gzj7Vv0Y61b6"
    "2ItW9llaYcKJ0/GsJX1ZyxCs2LaVdJyBQi0EeKQA8kQMRGiGdnRW64gs4diet6ESYo5ege"
    "c0Fp536CD3qIpJKo+7HNZiEtM+zuQ04pZ5zUAa7VjViuaSKo7SHXlV6MO2K8isiuW/Feqq"
    "YBz6N13VvuXUXpFqqyS6eEZkDrDMzNdAoqdwQyusZ6KYexq3usG5RvbIUEV1x6u5D+SFxl"
    "Tc1/RVxlTQlIcZV13mstrrLeDkFxlfXur7IWd3fV6VqXp8BXEWPPaFmS5KvrzFcs3YkDLD"
    "2U0w4k4clJzo5av5e7NzjHSTiesXXf713Lg0FQ6NpIlMPlAxz26+GI31upjROeTKCwinKg"
    "XPVG3Wt8SaQ9g10pn//kZMUmvbBHi1vCNvKiJ1biHrvRh5dJrXv/yjldksT3wmFvG9OmuF"
    "ltB8YMcbMadzuMCMLnNAIrra9noRlMt1AV3Svz6HEGqYz209lsXWIiwtAqOc5G/mZk/SPy"
    "piHHUZa4nT3k24c5sp/uE7smrhoS55oIGBfTKpwg12qBhBOkcII8QL3BZm569H3zkM/2V9"
    "t9uVHnhVhGsj7JMmIHwjf4QNHVuYhV2B8OUcQqfECswhsAL3rwhrA4YAjyZTXShUxBwWJu"
    "Ns7P4nWMvuQFkXd63Rvp+2XtZGwNR/IA/98YW1/lm274rQmf/DbqB19Ox9Ztv43/bY2tgT"
    "Qc9fGXM/hlFFA6zzEIrX4nBh3p7m5R0214CrAQnMxCl9MtVMOsLDz2P95jH1GJ9oJCV7gb"
    "6F5zyFtxGcEbsSbtcJArt/ci93WTN6AXUqdlrkxP9GnBAyW5LJ5f5ugAX7yNuCg1iZffqb"
    "q5EB8VLbSdslLrMghszU35LM0zftUsMylnO9V/ZrOBRJRZu3w2Lii7fDYulnsToWcL5sN1"
    "yrjyrooR8WowlHRjjPJdeUSQ0cQwgeKCCXCBtfbm6tJAL7ZSEmtLdedbL+G5H9xWtAy40M"
    "czXsPwhb9qd6X+93xl3lWOT+jV96EsLS5o4jBmEzNHNFCV1czcsyB1WdYMohcxOEVkgNQP"
    "SBlgOsO2MSKRFBcyADfLqoAQIIztwiorjO0VmlZ6McO5U7jDkOGPjOgS8cKroBTxwiJeuO"
    "RL/ZHxwv6bPWEVUhjT5nkFIh9bdlrNhDpHIUtoUEzVQwR9npeeh8IzWToRxuR5995K3ecB"
    "Xg0NKFgPwGhjzDbB9SLFFwMrr8CltFZzb6NZaIRnSNH+xhbPTAu8gblT1WOoRESeEjOnvo"
    "H/QfiLoxwHhEf8SGgfhfZRaB/5UVMJ7SOP0yq49I+IsaAWUBF7IW4SVUG6LuaEVqTcN7k4"
    "wHmKr4iiX2i+sRR9A6Pu7T7OgogXYuQgiO7Um7j2uqxx5Z0EyQbKbZc006lEx9qKAyy1Pe"
    "aeUIlwE3i8ZU+lhQMJgxB4NjPDOCBfVYQzryiT0KF0EweuHf4IgVzCIZjX6F9MuLBcnv7h"
    "UY54ruIaipZUEYf8nh3y9Nz/WZzxfPr/q0xzHqjbpzzYPK9mnuqy3pcHvbs/ZWU0kPtdqS"
    "Nf1uBhYZuvQIlcRcZWV/6q3LSlu94X2EfwpiTJj9jrj9HpyGoWItqldQnUjv64J/nIIYk/"
    "mxyuwI5QLvdk8mId9jnNzC16mZu/8IteyQs9kOcYsQGipV82p8TP/wOhEvcQ"
)
