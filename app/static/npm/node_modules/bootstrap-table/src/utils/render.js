export default {

  /**
   * Converts a class representation (string, array, or object) to a single
   * space-separated string. If the input is a string, it returns the string
   * as is. If it's an array, it recursively converts each element to a string
   * and joins them with spaces. If it's an object, it includes keys with truthy
   * values, joined by spaces. Returns an empty string for other types.
   *
   * @param {string|array|object} class_ - The class representation to convert.
   * @returns {string} - The space-separated class string.
   */
  classToString (class_) {
    if (typeof class_ === 'string') {
      return class_
    }
    if (Array.isArray(class_)) {
      return class_.map(x => this.classToString(x)).filter(x => x).join(' ')
    }
    if (class_ && typeof class_ === 'object') {
      return Object.entries(class_).map(([k, v]) => v ? k : '').filter(x => x).join(' ')
    }
    return ''
  },

  /**
   * Replaces all single quote characters with the HTML entity for a single quote.
   * This is useful for escaping apostrophes in text that will be inserted into an
   * HTML attribute.
   *
   * @param {*} value - The value to escape.
   * @returns {string} - The escaped string.
   */
  escapeApostrophe (value) {
    return value.toString()
      .replace(/'/g, '&#39;')
  },

  /**
   * Escapes a given string for safe insertion into HTML.
   * This will replace all occurrences of &, <, >, ", and ' with their
   * corresponding HTML entities (&amp;, &lt;, &gt;, &quot;, and &#39;).
   *
   * @param {*} text - The text to escape.
   * @returns {string} - The escaped string.
   */
  escapeHTML (text) {
    if (!text) {
      return text
    }
    return text.toString()
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
  },

  /**
   * Creates an HTML element with the specified attributes and children.
   * If the element is not an instance of HTMLElement, it will be created
   * using document.createElement. Supports special handling for attributes
   * such as text, innerHTML, class, style, and event handlers.
   *
   * @param {string|HTMLElement} element - The element tag name or HTMLElement instance.
   * @param {object} [attrs] - An object representing attributes to set on the element.
   *                           Special keys:
   *                           - 'text' or 'innerText' sets the text content.
   *                           - 'html' or 'innerHTML' sets the HTML content.
   *                           - 'class' converts to a string using classToString.
   *                           - 'style' can be a string or an object parsed by parseStyle.
   *                           - '@event' or 'onEvent' adds an event listener for the event.
   *                           - '.property' sets a property on the element.
   * @param {Array} [children] - An array of child nodes to append to the element.
   * @returns {HTMLElement} - The created HTML element with applied attributes and children.
   */
  h (element, attrs, children) {
    const el = element instanceof HTMLElement ? element : document.createElement(element)
    const _attrs = attrs || {}
    const _children = children || []

    // default attributes
    if (el.tagName === 'A') {
      el.href = 'javascript:'
    }

    for (const [k, v] of Object.entries(_attrs)) {
      if (v === undefined) {
        continue
      }
      if (['text', 'innerText'].includes(k)) {
        el.innerText = v
      } else if (['html', 'innerHTML'].includes(k)) {
        el.innerHTML = v
      } else if (k === 'children') {
        _children.push(...v)
      } else if (k === 'class') {
        el.setAttribute('class', this.classToString(v))
      } else if (k === 'style') {
        if (typeof v === 'string') {
          el.setAttribute('style', v)
        } else {
          this.parseStyle(el, v)
        }
      } else if (k.startsWith('@') || k.startsWith('on')) {
        // event handlers
        const event = k.startsWith('@') ? k.substring(1) : k.substring(2).toLowerCase()
        const args = Array.isArray(v) ? v : [v]

        el.addEventListener(event, ...args)
      } else if (k.startsWith('.')) {
        // set property
        el[k.substring(1)] = v
      } else {
        el.setAttribute(k, v)
      }
    }
    if (_children.length) {
      el.append(..._children)
    }
    return el
  },

  /**
   * Converts the given HTML string or Node to an array of nodes.
   * If given a jQuery object, it returns the underlying node array.
   * If given a Node, it returns an array containing the node.
   * If given a string, it parses the string as HTML and returns the
   * resulting child nodes in an array.
   *
   * @param {string|Node|jQuery} html - The HTML string or Node to convert.
   * @returns {Node[]} - An array of child nodes.
   */
  htmlToNodes (html) {
    if (html instanceof $) {
      return html.get()
    }
    if (html instanceof Node) {
      return [html]
    }
    if (typeof html !== 'string') {
      html = new String(html).toString()
    }
    const d = document.createElement('div')

    d.innerHTML = html
    return d.childNodes
  },

  /**
   * Sets the given style attributes on the given DOM element.
   * If given a string, it expects a CSS style string and parses it
   * into individual style attributes. If given an array, it iterates
   * over the array and calls itself with each item. If given an object,
   * it iterates over the key-value pairs and calls itself with each
   * pair. In all cases, it sets the style attributes directly on the
   * given DOM element.
   *
   * @param {Node} dom - The DOM element to set the style attributes on.
   * @param {string|object|array} style - The style attributes to set.
   * @returns {Node} - The same DOM element.
   */
  parseStyle (dom, style) {
    if (!style) {
      return dom
    }
    if (typeof style === 'string') {
      style.split(';').forEach(i => {
        const index = i.indexOf(':')

        if (index > 0) {
          const k = i.substring(0, index).trim()
          const v = i.substring(index + 1).trim()

          dom.style.setProperty(k, v)
        }
      })
    } else if (Array.isArray(style)) {
      for (const item of style) {
        this.parseStyle(dom, item)
      }
    } else if (typeof style === 'object') {
      for (const [k, v] of Object.entries(style)) {
        dom.style.setProperty(k, v)
      }
    }
    return dom
  },

  /**
   * Removes all HTML tags from the given string.
   * If the given string is null or undefined, it returns the same value.
   * Otherwise, it uses a regular expression to remove all HTML tags and
   * HTML entities, and then trims the result.
   *
   * @param {*} text - The string from which to remove HTML tags.
   * @returns {string} - The string with all HTML tags removed.
   */
  removeHTML (text) {
    if (!text) {
      return text
    }
    return text.toString()
      .replace(/(<([^>]+)>)/ig, '')
      .replace(/&[#A-Za-z0-9]+;/gi, '')
      .trim()
  },

  /**
   * Replaces all occurrences of the given search text with a mark tag
   * in the given HTML string or Node.
   * If the given string is null or undefined, it returns the same value.
   * Otherwise, it uses a regular expression to find all occurrences of the
   * search text and replaces them with a mark tag containing the matching
   * text.
   *
   * @param {string|Node} html - The HTML string or Node to search for the
   *     given search text.
   * @param {string} searchText - The search text to look for in the given
   *     HTML string or Node.
   * @returns {string|Node} - The modified HTML string or Node with all
   *     occurrences of the search text replaced with a mark tag.
   */
  replaceSearchMark (html, searchText) {
    const isDom = html instanceof Element
    const node = isDom ? html : document.createElement('div')
    const regExp = new RegExp(searchText, 'gim')
    const replaceTextWithDom = (text, regExp) => {
      const result = []
      let match
      let lastIndex = 0

      while ((match = regExp.exec(text)) !== null) {
        if (lastIndex !== match.index) {
          result.push(document.createTextNode(text.substring(lastIndex, match.index)))
        }
        const mark = document.createElement('mark')

        mark.innerText = match[0]
        result.push(mark)
        lastIndex = match.index + match[0].length
      }
      if (!result.length) {
        // no match
        return
      }
      if (lastIndex !== text.length) {
        result.push(document.createTextNode(text.substring(lastIndex)))
      }
      return result
    }
    const replaceMark = node => {
      for (let i = 0; i < node.childNodes.length; i++) {
        const child = node.childNodes[i]

        if (child.nodeType === document.TEXT_NODE) {
          const elements = replaceTextWithDom(child.data, regExp)

          if (elements) {
            for (const el of elements) {
              node.insertBefore(el, child)
            }
            node.removeChild(child)
            i += elements.length - 1
          }
        }
        if (child.nodeType === document.ELEMENT_NODE) {
          replaceMark(child)
        }
      }
    }

    if (!isDom) {
      node.innerHTML = html
    }
    replaceMark(node)
    return isDom ? node : node.innerHTML
  },

  /**
   * Unescapes a given string from HTML entities.
   * If the given string is null or undefined, it returns the same value.
   * Otherwise, it uses a regular expression to unescape the string and
   * then trims the result.
   *
   * @param {*} text - The string to unescape.
   * @returns {string} - The unescaped string.
   */
  unescapeHTML (text) {
    if (typeof text !== 'string' || !text) {
      return text
    }
    return text.toString()
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, '\'')
  }
}
