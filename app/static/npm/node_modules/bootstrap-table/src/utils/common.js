export default {

  /**
   * Compares two objects by their keys and values.
   * @param {Object} objectA
   * @param {Object} objectB
   * @param {boolean} [compareLength=false] - if true, compare the number of keys before comparing the values
   * @returns {boolean} - true if the objects are equal, false if they are not
   */
  compareObjects (objectA, objectB, compareLength) {
    const aKeys = Object.keys(objectA)
    const bKeys = Object.keys(objectB)

    if (compareLength && aKeys.length !== bKeys.length) {
      return false
    }

    for (const key of aKeys) {
      if (bKeys.includes(key) && objectA[key] !== objectB[key]) {
        return false
      }
    }

    return true
  },

  /**
   * Creates a debounced function that delays the invocation of `func` until after
   * `wait` milliseconds have elapsed since the last time the debounced function
   * was invoked. Optionally, `func` can be invoked on the leading edge instead
   * of the trailing edge of the wait interval if `immediate` is set to true.
   *
   * @param {Function} func The function to debounce.
   * @param {number} wait The number of milliseconds to delay.
   * @param {boolean} [immediate=false] If true, triggers the function on the leading edge,
   *                                    instead of the trailing edge of the wait interval.
   * @returns {Function} Returns the new debounced function.
   */
  debounce (func, wait, immediate) {
    let timeout

    return function executedFunction () {
      const context = this
      const args = arguments

      const later = function () {
        timeout = null
        if (!immediate) func.apply(context, args)
      }

      const callNow = immediate && !timeout

      clearTimeout(timeout)

      timeout = setTimeout(later, wait)

      if (callNow) func.apply(context, args)
    }
  },

  /**
   * Creates a deep copy of the provided argument.
   *
   * @param {*} arg The value to be copied. Can be an object or an array.
   * @returns {*} A new deep copy of the argument. If the argument is undefined,
   *              it returns undefined.
   */
  deepCopy (arg) {
    if (arg === undefined) {
      return arg
    }
    return this.extend(true, Array.isArray(arg) ? [] : {}, arg)
  },

  /**
   * $.extend: https://github.com/jquery/jquery/blob/3.6.2/src/core.js#L132
   * Extends the target object with properties from subsequent objects.
   * Supports both shallow and deep copying.
   *
   * @param {...*} args - The first argument can be a boolean indicating
   *                      whether to perform a deep copy. Subsequent
   *                      arguments are objects whose properties will be
   *                      copied to the target object.
   * @returns {Object} The extended target object.
   *
   * - If the first argument is a boolean and true, a deep copy is
   *   performed, recursively merging objects and arrays.
   * - If the first argument is not an object or function, an empty
   *   object is used as the target.
   * - Prevents Object.prototype pollution and handles circular
   *   references by avoiding self-references.
   */
  extend (...args) {
    let target = args[0] || {}
    let i = 1
    let deep = false
    let clone

    // Handle a deep copy situation
    if (typeof target === 'boolean') {
      deep = target

      // Skip the boolean and the target
      target = args[i] || {}
      i++
    }

    // Handle case when target is a string or something (possible in deep copy)
    if (typeof target !== 'object' && typeof target !== 'function') {
      target = {}
    }

    for (; i < args.length; i++) {
      const options = args[i]

      // Ignore undefined/null values
      if (typeof options === 'undefined' || options === null) {
        continue
      }

      // Extend the base object
      // eslint-disable-next-line guard-for-in
      for (const name in options) {
        const copy = options[name]

        // Prevent Object.prototype pollution
        // Prevent never-ending loop
        if (name === '__proto__' || target === copy) {
          continue
        }

        const copyIsArray = Array.isArray(copy)

        // Recurse if we're merging plain objects or arrays
        if (deep && copy && (this.isObject(copy) || copyIsArray)) {
          const src = target[name]

          if (copyIsArray && Array.isArray(src)) {
            if (src.every(it => !this.isObject(it) && !Array.isArray(it))) {
              target[name] = copy
              continue
            }
          }

          if (copyIsArray && !Array.isArray(src)) {
            clone = []
          } else if (!copyIsArray && !this.isObject(src)) {
            clone = {}
          } else {
            clone = src
          }

          // Never move original objects, clone them
          target[name] = this.extend(deep, clone, copy)

        // Don't bring in undefined values
        } else if (copy !== undefined) {
          target[name] = copy
        }
      }
    }

    return target
  },

  /**
   * Check if an object is empty.
   *
   * @param {Object} [obj={}] Object to check.
   * @return {boolean} `true` if object is empty, `false` otherwise.
   */
  isEmptyObject (obj = {}) {
    return Object.entries(obj).length === 0 && obj.constructor === Object
  },

  /**
   * Checks if a value is numeric.
   *
   * @param {*} n The value to check.
   * @return {boolean} `true` if the value is numeric, `false` otherwise.
   */
  isNumeric (n) {
    return !isNaN(parseFloat(n)) && isFinite(n)
  },

  /**
   * Check if `obj` is an object.
   *
   * @param {*} obj
   * @return {boolean}
   */
  isObject (obj) {
    if (typeof obj !== 'object' || obj === null) {
      return false
    }

    let proto = obj

    while (Object.getPrototypeOf(proto) !== null) {
      proto = Object.getPrototypeOf(proto)
    }

    return Object.getPrototypeOf(obj) === proto
  },

  /**
   * Removes accents from a string.
   *
   * @param {string} value
   * @return {string}
   */
  normalizeAccent (value) {
    if (typeof value !== 'string') {
      return value
    }
    return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  },

  /**
   * Only support '%s' and return '' when arguments are undefined.
   *
   * @param {string} _str
   * @param {...*} args
   * @returns {string}
   */
  sprintf (_str, ...args) {
    let flag = true
    let i = 0

    const str = _str.replace(/%s/g, () => {
      const arg = args[i++]

      if (typeof arg === 'undefined') {
        flag = false
        return ''
      }
      return arg
    })

    return flag ? str : ''
  }
}
