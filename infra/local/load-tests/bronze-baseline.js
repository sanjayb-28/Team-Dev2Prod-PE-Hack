import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  vus: Number(__ENV.VUS || 50),
  duration: __ENV.DURATION || '30s',
}

const baseUrl = __ENV.BASE_URL || 'http://workload-api:5000'

export default function () {
  const health = http.get(`${baseUrl}/health`)
  check(health, {
    'health returns 200': (response) => response.status === 200,
  })

  const urls = http.get(`${baseUrl}/urls`)
  check(urls, {
    'urls returns 200': (response) => response.status === 200,
  })

  sleep(1)
}
