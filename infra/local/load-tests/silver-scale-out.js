import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  vus: Number(__ENV.VUS || 200),
  duration: __ENV.DURATION || '45s',
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.05'],
  },
}

const baseUrl = __ENV.BASE_URL || 'http://scale-gateway:8080'

export default function () {
  const paths = ['/health', '/urls', '/urls?is_active=true']
  const path = paths[Math.floor(Math.random() * paths.length)]
  const response = http.get(`${baseUrl}${path}`)

  check(response, {
    'scale path returns 200': (result) => result.status === 200,
    'gateway reports upstream': (result) =>
      typeof result.headers['X-Scale-Upstream'] === 'string' &&
      result.headers['X-Scale-Upstream'].length > 0,
  })

  sleep(1)
}
