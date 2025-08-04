import fs from 'fs'

const test = fs.readFileSync('./test.json', 'utf8')
const fields = JSON.parse(test)
const hasSpace = value => {
  if (typeof value === 'string' && (value.startsWith(' ') || value.endsWith(' '))) {
    return true
  }
  if (Array.isArray(value)) {
    for (const v of value) {
      return hasSpace(v)
    }
  }
  return false
}

for (const item of fields.custom_fields) {
  for (const value of Object.values(item)) {
    // console.log(typeof value)

    if (hasSpace(value)) {
      console.log('error', item.name, value)
    }
  }
}
