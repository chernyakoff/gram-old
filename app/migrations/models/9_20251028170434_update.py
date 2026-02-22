from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "app_settings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "section" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "value" TEXT,
    CONSTRAINT "uid_app_setting_section_5cfa7d" UNIQUE ("section", "name")
);
CREATE INDEX IF NOT EXISTS "idx_app_setting_section_5cfa7d" ON "app_settings" ("section", "name");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "app_settings";"""


MODELS_STATE = (
    "eJztXWtz4jYX/isMn7YzaSdcEpJ8I8TJ8jZABkjbbbLjUWwBftfYrm02YTr73yvLN/kWjC"
    "2xjvAXEmRxJD3nSDo6F/nf5lqXoWr99mhBs3nV+LcJDAP99YqbJ42mBtYwLHEromIbvKi4"
    "fIMKcEVFk+EbtFDZ01f0dQ00sIQy+qptVBUVgBfLNoFko5IFUC2Iioxv4kKBqoxb9htSZI"
    "faRlP+2TjfbXPjVJXhAmxUOyTnNieHNZxyr1M+fflFlHR1s9ZCurIuoW4o2jKktIQaNIGN"
    "afm/xN0S7a2Bu3StLIeafYu7ih5KuuYMRdFsC/d86VT69bLd7nR67dPO+cVZt9c7uzi9QH"
    "Vxf5KPej/wmCzJVAxb0bWwN8bWXula0DRqpOmOJOyS2yru2PBuOJ47FXQErcsQp+DHj/Sh"
    "LjzAQy6117ESva3HSmRgA6Io5JRkQgc2EdgRjgXoZ7PMrwI2ti5q+itRRLDRZz3JxWibhb"
    "h5g57ayhpm8hM1IU80det1IS+rZI/ub/4/TWKEIpDlyJDS2DkfjoTZvD96cH65tqx/VNzf"
    "/lxwnrRx6TZW+un8lyj/AyKNP4fzzw3na+PvyVhwahm6ZS9N3GJYb/43lpeQrxtDpsfX5O"
    "xMY2u0yZqtTNiKVmr8/55MzclBgnoh/g1WwMzk3Rq8iSrUlvYKfe108/IO0Xhn9fyjPx18"
    "7k8/dboxrMfekzZ+FEVxoZiWLRbBMecKF22AMZTnlKE8z4byPAGlCtgiGaHPM5DGSkfL0c"
    "ZUGQEZoc8YyPbZOV0kEcFMKPGzKJamru6Sx9NdGKbqnz7hQvgh9VPQNmsM4RChBzQJZqui"
    "nXbvPFA+nS8p6mbzcSZM0Vietf7NaDi+avSa+2qfs1H//t5XN4lprUhQs6AINVl09szDKY"
    "dpLTPRJWjqDoSwVEx5+Jo1Speboq0vob3CB0d8UHgB0rdXYMpi5JgRCgaQJH3jIFh+lQp+"
    "Veg45/Xz9vcpVAEeWnEWe+fivju2pi+SPq1Q2QxxWANFRV3mEoeRO7ZcOBim/n8o8SkPD+"
    "7Y8uLwpkBeYXjb5gLBgrbN66SYEWNLBSKyesYsME5bETTzmOkC3AM7HSFkXFjqPFoJNWmH"
    "la7d6va6F53zbqAfBSWUbHK57W/Rk/nh5R6NCMkKtF0FvT8b9G+wQmCC14DZuGuiy5Ao1L"
    "e6CZWl9jvc7lJK95wsvoU5c6LUNssU6T5641Zts+SRrStUi+bKSPLPp821ZUg3meHn0y5q"
    "0KjMTl3eRJ4XsgMaydtnZ7TtaGfv2NHOEpIHLOtVN2Vm0kfQ5xxKpIor33fJpLec7w9kSL"
    "3YeUnXVQi0spayF0TmPUf3ZHIf2YmuhzG39/hxdC1MP7UwsKiS4uq1yTmO7TTmlpVcEuRZ"
    "iyVlocwWyYTjRpe+IcUHDVQp7HIoYN2NtVpbdqmoWA6sogUtyzN1sHDExZpg7R+m7EHqZD"
    "uQOgn/EXFgZqVBiMcVyrSPG+Ip0OoDzZdQuQKd4Wu2uyKnKa4PTUVaNfPY4ryqJ4QxDgRF"
    "tS2uEra40nal79CktICmsoEgz7uyi2YTIxA90owBbJ2e0gUQEcwEED+L67eaDTVmp36CfC"
    "Eg/zebjMsqX48aevokK5J90lAVy/76DopOexEFywfv06j/VxzXwf3kOq45OQSuqXnDc24v"
    "NwpQ9WWu7cWrSm4vMi7i3NfzATWZHBtRIlqion4hr3eHdQ3tCrLIs4sTkV5QUgwlvlSWkm"
    "yKAAe9S4V4osG5jj4oAzwlIcmEOFMJQt2wN7s8+AhJxW7mlllysQjpF97Dc0XRRfbzi5TY"
    "ueF4OL9qOAN51oTxXf9OuGqg+mhpfdYmt7dOYJ2+WEDzWUM7ymw4vrtqSKpuof6iksno4V"
    "6Yo19I+trAYlBUM7jI1Asu4loBGqzJ0u+ZxS+z9pCxNd8skBRaqwN7tGON1pY4KqyM7qlM"
    "TkCRFo7FgBQJ745tq/Q12ngLx4Iy7WjhNbQstKFyGRA4csf2rpaVxwjp6cO5rJCh7hyaIY"
    "mAbC4OitxMpvSh1uGDJcMHU6LPKbq8KOLmde6w0O2KWa+DL+szSB18eURspRcNV2eM1xnj"
    "dcZ4dYA0EH1WIAa0WU9qygFwnewIuE4iBA686BuaumPESuPTZgxgj7Kjupftp+4l3dQroG"
    "mQ1Y0FBHWetxb7VV8ARhAGtHleB4FhsDS3BtQ5ypFwBrUC1oolaD59nkWPXshtuu+tZLjt"
    "HL5lSh8d1ObCX/PIAScRmRMccu4n4zu/ejxcJ4qqDL8rEhSxRYPRwhhvgmsh3Vo2XIv0oh"
    "vTAE02wjOkzvrGFs9YC1yDWadGUUyNetlYu/Ki/JL9wfSJHweUhgnXymbNDE2C/nEAWqft"
    "lU7be9XNb7SSk9L2nQh9nncdNHOcW+beDMWE1kG9WWkt19FXVLwd2PYLTVOn4UvPNC4HDR"
    "zToQyPHNhIyTfsw06XZMP1bKEyW6IBCiy8CJEGOLKf1QnCPzdB2IPeg+mdTOCY7um95oK3"
    "UEQvLrAvOZUH7kCbvlC9Gz/lXApNA5L9wqcOhsiDM75cSBDpdrxJR5hcWCZO1b8UNk+cKn"
    "GBbBCnSl6Yy0Wc6lEmNNILuGQRqVrJiMu43lBR7CoW5Vs6TpVhhFGp4KIPevxjHfabbtCr"
    "436ZHwJZJ5WmOgvZ55Qe32m+TiLlhpX5cvBlEyw+UhL+ZUoS/s20fzu/auChPGvTx/EYJ9"
    "qbG03Difa3w/Fw9lm4QT3xJO1ZG/THA+H+3imUnIZVFWKxKeQzuMx0GVwm4m1pmssyHIK1"
    "vay2l/2UTN0g45lLE0i+O1HyWEG8pN9cVpAwQTi0ghAJ0bUVpELzKX2kGZNFDixqFTzIu5"
    "077FE+h4mx1GHegghFqpaTaJitT/0na0P9wWDyOEb6kJfUjzQiYTB8GApOWbBCP2uzL7O5"
    "MLpquEGXh9B97KXoLV3svIWJNo5lL48ADd9YpST5pGuzVW22+vBmq8gux2JTiDRwLCsRnV"
    "NFTl3ad5zk0aUJJwv5Nrzg1ZP86tJVOtDX99lU0dNV38jC5xZX38jCJVtZvpvsGK69yOUc"
    "KZwuVtIz8uFScjw1V1XWyq5lpnVaRpEOWqiEW6P5vDnttlvOZwcSn7ike4n/P8OfMv68wJ"
    "+XDfyn3SB+0SVqQbLWIiTSPSUILkKCXbcDwH2aYsfZ18+ib2xRBoq6zcXQ80L8TGmjOixt"
    "Ebh2z+Js6i4I9ro1zxoEI/aVhG7rfUnouP+7lU4JXoOwpNsJf9Ztu+WkmHlj6RDP3V9fUJ"
    "AXx/IpOpupiEMydshLsfmf0kaF5EUmONEj+PRCsq6dmMRSUi4aRKVTgnPu5wtBlQX/0D87"
    "uNfulGSf10SFmAeIuSYTy+15xdnmXva2Dv2DLHTBRCPHZPc1TH1tsHtrckD9uF6fVId0VN"
    "/4mngVAcfpPZk2NVJQycQT3uJaiESbMlEtM2jbGKI8pvig8glhi7eIwtoWX9viT47UFm9B"
    "yZ/ZbCJVAvKcv0KUAyvpz4bwO1A3rFKgAtrHdKioVd6fm/VPAEQshJg75V8GHoYI51GCIg"
    "HFgRYUDaIm9KAnXwv1ux94GRKXAaHuPqWUcqZJfUBZ3UvlWoeKeQW1rqgwHkjxynNWKaV7"
    "UXzVReb6fKh3XbQpX+uOCL5zMX7iYvc1tIGDMyPtgSR/vBa0fFl+BtRkb9p8kDy/VorsNh"
    "+E8Q1O7fPG86w9TCcDYea+WNcwdcm569opn+FodwsHut/2hzjPb4HWDif173ryOB44BS/6"
    "BnWleNpfK3s6tBKzob5zkVLoRn3nIofJyt7VfLsWsmLOY5J4JRyPZUx29T2VBzik1/dUcr"
    "fC1Ek8nIbCRs+hLM5s0RZqsxqlNB4GqdA0XMwTDc519HG4uxMJA2LfMPbyo5L1T8gXehuG"
    "mOFOfUq3e3JkF6ySurbT3Fd7C6vi6qq9hbW3sAoHkf38WfSdWJFrj3NtQrF7ksNdyH0ghj"
    "dE8xvW8wE1vBy7UyIQ8OBKWi5flC9oB/VF7YofLL2z2ywPNfaxnWcikd3AXrFZQHzKjDf6"
    "VvuC7kaPCGY7M5xniUP3Lo3TLyl03i6ub3645Em0dkHLYvsm3WgTxzjjF4oKRRMuoAm9xZ"
    "9Nuky8lYJYa8Dclhbhre3eEZgFnOdiDmQYTfjr4bg//ZKusV6nuKSvv8yFflKgic2YxWtN"
    "Iw0cizQf9Fqd1JfB7HEWSLxFJnEmALiGKIVV+D0bfCiDFAuVn0X8GZ86P2BqzAPlbXn7h/"
    "KkRYs0p8Jscv+HID7OhOm4PxKcqyktXf0ORT9C7lkbC3+KN8P+/eQO9RG+iqGbgH2UieMV"
    "Y8UFn3ZhfyBVr+47yDleu7S37+4ApliURjix+AnRoKoKZan2tS70ri70RO5jxALoiH5RY+"
    "mP/wDouYQ2"
)
