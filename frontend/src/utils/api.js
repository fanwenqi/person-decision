// 后端 API 封装（uni.request 兼容 App / H5 / 小程序）
//
// 默认使用相对路径 '/api'，配合 vite 开发代理（见 vite.config.js）或同源部署。
// 若打包成独立 App（Android/iOS），后端不在同源，请调用 setApiBase('http://<你的IP>:8000/api')
// 设置真实可达地址（例如手机与电脑同一局域网时的电脑 IP）。

const DEFAULT_BASE = '/api'

function getBase() {
  try {
    return uni.getStorageSync('API_BASE') || DEFAULT_BASE
  } catch (e) {
    return DEFAULT_BASE
  }
}

export function setApiBase(url) {
  try {
    uni.setStorageSync('API_BASE', url.replace(/\/+$/, ''))
  } catch (e) {}
}

export function getApiBase() {
  return getBase()
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getBase() + path,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res.data || res)
        }
      },
      fail: (err) => reject(err)
    })
  })
}

export function createSession() {
  return request('POST', '/sessions')
}

export function getSession(id) {
  return request('GET', `/sessions/${id}`)
}

export function sendMessage(id, text) {
  return request('POST', `/sessions/${id}/messages`, { text })
}
