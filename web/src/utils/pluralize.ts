export function pluralize(count: number, forms: [string, string, string]) {
  const mod10 = count % 10
  const mod100 = count % 100

  if (mod10 === 1 && mod100 !== 11) {
    return forms[0] // 1 аккаунт
  } else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) {
    return forms[1] // 2,3,4 аккаунта
  } else {
    return forms[2] // 5+ аккаунтов
  }
}
