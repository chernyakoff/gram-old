import fs from 'fs'
const getTimezoneOffset = (timezoneName) => {
  const date = new Date()

  const formatter = new Intl.DateTimeFormat('en', {
    timeZone: timezoneName,
    timeZoneName: 'longOffset',
  })

  const parts = formatter.formatToParts(date)
  const timeZonePart = parts.find((part) => part.type === 'timeZoneName')

  if (timeZonePart?.value) {
    const match = timeZonePart.value.match(/GMT([+-])(\d{2}):(\d{2})/)
    if (match) {
      const sign = match[1] === '+' ? 1 : -1
      const hours = parseInt(match[2], 10)
      const minutes = parseInt(match[3], 10)
      return sign * (hours + minutes / 60)
    }
  }

  return 0
}

const formatOffset = (offset) => {
  const hours = Math.floor(Math.abs(offset))
  const minutes = Math.round((Math.abs(offset) - hours) * 60)
  const sign = offset >= 0 ? '+' : '-'

  if (minutes === 0) {
    return `UTC${sign}${hours}`
  }
  return `UTC${sign}${hours}:${minutes.toString().padStart(2, '0')}`
}

const timezones = Intl.supportedValuesOf('timeZone')
  .map((tz) => {
    const offset = getTimezoneOffset(tz)
    return {
      value: tz,
      label: `${tz.replace(/_/g, ' ')} (${formatOffset(offset)})`,
      offset,
    }
  })
  .sort((a, b) => a.offset - b.offset)

fs.writeFileSync('./src//utils/timezones.json', JSON.stringify(timezones, null, 2))

console.log(`Generated ${timezones.length} timezones`)
