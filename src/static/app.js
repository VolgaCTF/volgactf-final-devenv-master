(function () {
  document.addEventListener('DOMContentLoaded', function (event) {
    function onClearFlags () {
      fetch('/flags', {
        method: 'DELETE'
      })
      .then(function (data) {
      })
      .catch(function (err) {
        console.log(err)
      })
    }

    var flagsClearButton = document.getElementById('clear_flags')
    flagsClearButton.onclick = onClearFlags

    var flagsContainerEl = document.getElementById('flags')

    function onRequestPull () {
      var flag = this.getAttribute('data-flag')
      var form = new FormData()
      form.append('flag', flag)
      fetch('/pull', {
        method: 'POST',
        body: form
      })
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
      })
      .catch(function (err) {
        console.log(err)
      })
    }

    function renderFlags (flags) {
      while (flagsContainerEl.firstChild) {
        flagsContainerEl.removeChild(flagsContainerEl.firstChild);
      }

      for (var i = 0; i < flags.length; ++i) {
        var item = flags[i]
        var itemEl = document.createElement('li')
        itemEl.className = 'list-group-item'

        var leftEl = document.createElement('div')
        leftEl.className = 'float-left'

        var flagEl = document.createElement('code')
        var flagTextEl = document.createTextNode(item.flag)
        flagEl.appendChild(flagTextEl)
        leftEl.appendChild(flagEl)
        var br1El = document.createElement('br')
        leftEl.appendChild(br1El)

        if (item.hasOwnProperty('expires')) {
          var expiresEl = document.createElement('small')
          var expiresTextEl = document.createTextNode('expires on ' + new Date(item.expires).toUTCString())
          expiresEl.appendChild(expiresTextEl)
          leftEl.appendChild(expiresEl)
          var br2El = document.createElement('br')
          leftEl.appendChild(br2El)
        }

        var labelEl = document.createElement('code')
        labelEl.style.color = 'gray'
        var smallEl = document.createElement('small')
        var labelTextEl = document.createTextNode(item.label)
        smallEl.appendChild(labelTextEl)
        labelEl.appendChild(smallEl)
        leftEl.appendChild(labelEl)

        var rightEl = document.createElement('div')
        rightEl.className = 'float-right'

        var buttonEl = document.createElement('button')
        buttonEl.className = 'btn btn-outline-primary btn-sm'
        var buttonTextEl = document.createTextNode('PULL')
        buttonEl.appendChild(buttonTextEl)
        buttonEl.disabled = item.status !== 101
        buttonEl.onclick = onRequestPull
        buttonEl.setAttribute('data-flag', item.flag)
        rightEl.appendChild(buttonEl)

        itemEl.appendChild(leftEl)
        itemEl.appendChild(rightEl)

        flagsContainerEl.appendChild(itemEl)
      }
    }

    function onClearLogs () {
      fetch('/logs', {
        method: 'DELETE'
      })
      .then(function (data) {
      })
      .catch(function (err) {
        console.log(err)
      })
    }

    var logsClearButton = document.getElementById('clear_logs')
    logsClearButton.onclick = onClearLogs

    var logsContainerEl = document.getElementById('logs')

    function renderLogs (logs) {
      while (logsContainerEl.firstChild) {
        logsContainerEl.removeChild(logsContainerEl.firstChild);
      }

      for (var i=0; i<logs.length; ++i) {
        var item = logs[i]
        var itemEl = document.createElement('li')
        itemEl.className = 'list-group-item'

        var headerEl = document.createElement('p')

        var itemTypeEl = document.createElement('span')
        if (item.type === 'egress') {
          itemTypeEl.className = 'badge badge-danger'
        } else {
          itemTypeEl.className = 'badge badge-primary'
        }
        var itemTypeTextEl = document.createTextNode((item.type === 'egress') ? 'egress' : 'ingress')
        itemTypeEl.appendChild(itemTypeTextEl)
        headerEl.appendChild(itemTypeEl)
        headerEl.appendChild(document.createTextNode('\u00A0'))

        var itemTimestampEl = document.createElement('code')
        var itemTimestampTextEl = document.createTextNode('[' + new Date(item.timestamp).toUTCString() + ']')
        itemTimestampEl.appendChild(itemTimestampTextEl)
        headerEl.appendChild(itemTimestampEl)
        headerEl.appendChild(document.createTextNode('\u00A0'))

        var itemCategoryEl = document.createElement('span')
        itemCategoryEl.className = 'badge badge-info'
        var itemCategoryTextEl = document.createTextNode(item.category)
        itemCategoryEl.appendChild(itemCategoryTextEl)
        headerEl.appendChild(itemCategoryEl)

        if (item.type === 'ingress') {
          headerEl.appendChild(document.createTextNode('\u00A0'))

          var itemStatusSpanEl = document.createElement('span')
          var statusText = null
          switch (item.raw.status) {
            case 101:
              itemStatusSpanEl.className = 'badge badge-success'
              statusText = 'UP'
              break
            case 102:
              itemStatusSpanEl.className = 'badge badge-warning'
              statusText = 'CORRUPT'
              break
            case 103:
              itemStatusSpanEl.className = 'badge badge-dark'
              statusText = 'MUMBLE'
              break
            case 104:
              itemStatusSpanEl.className = 'badge badge-danger'
              statusText = 'DOWN'
              break
            case 110:
              itemStatusSpanEl.className = 'badge badge-secondary'
              statusText = 'INTERNAL_ERROR'
              break
            default:
              itemStatusSpanEl.className = 'badge badge-secondary'
              statusText = 'N/A'
              break
          }
          var itemStatusTextEl = document.createTextNode(statusText)
          itemStatusSpanEl.appendChild(itemStatusTextEl)
          headerEl.appendChild(itemStatusSpanEl)
        }

        itemEl.appendChild(headerEl)

        var detailsEl = document.createElement('details')
        detailsEl.style.margin = '10px 0'
        detailsEl.style.color = 'gray'
        var summaryEl = document.createElement('summary')
        var summaryTextEl = document.createTextNode('Data')
        summaryEl.appendChild(summaryTextEl)
        detailsEl.appendChild(summaryEl)

        var codeEl = document.createElement('code')
        codeEl.style.wordWrap = 'break-word'
        var codeTextEl = document.createTextNode(JSON.stringify(item.raw))
        codeEl.appendChild(codeTextEl)
        detailsEl.appendChild(codeEl)
        itemEl.appendChild(detailsEl)

        logsContainerEl.appendChild(itemEl)
      }
    }

    function loadLogs () {
      fetch('/logs')
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
        renderLogs(data)
      })
      .catch(function (err) {
        console.log(err)
      })
    }

    function loadFlags () {
      fetch('/flags')
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
        renderFlags(data)
      })
      .catch(function (err) {
        console.log(err)
      })
    }

    function combineForms(form1, form2) {
      var form1Data = new FormData(form1)
      var form2Data = new FormData(form2)
      for (var entry of form2Data.entries()) {
        form1Data.append(entry[0], entry[1])
      }
      return form1Data
    }

    var settingsForm = document.getElementById('settings')
    var onetimeForm = document.getElementById('onetime')
    onetimeForm.addEventListener('submit', function (e) {
      e.preventDefault()
      fetch('/onetime_push', {
        method: 'POST',
        body: combineForms(settingsForm, onetimeForm)
      })
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
      })
      .catch(function (err) {
        console.log(err)
      })
    }, false)

    var source = new EventSource(window.streamUrl)
    source.addEventListener('logs', function (e) {
      var data = JSON.parse(e.data)
      renderLogs(data)
    }, false)

    source.addEventListener('flags', function (e) {
      var data = JSON.parse(e.data)
      renderFlags(data)
    }, false)

    source.addEventListener('error', function (e) {
      console.log('Failed to connect to event stream. Is Redis running?')
    }, false)

    loadLogs()
    loadFlags()

    function updateState (state) {
      document.querySelector('#settings_checker_host').disabled = state.mode === 'recurring'
      document.querySelector('#settings_team_host').disabled = state.mode === 'recurring'
      document.querySelector('#settings_team_name').disabled = state.mode === 'recurring'
      document.querySelector('#settings_service_name').disabled = state.mode === 'recurring'

      document.querySelector('#onetime button[type="submit"]').disabled = state.mode === 'recurring'
      document.querySelector('#onetime_round').disabled = state.mode === 'recurring'

      document.querySelector('#recurring button[type="submit"]').disabled = state.mode === 'recurring'
      document.querySelector('#recurring_stop').disabled = state.mode !== 'recurring'

      document.querySelector('#recurring_flag_lifetime').disabled = state.mode === 'recurring'
      document.querySelector('#recurring_round_timespan').disabled = state.mode === 'recurring'
      document.querySelector('#recurring_poll_timespan').disabled = state.mode === 'recurring'
      document.querySelector('#recurring_poll_delay').disabled = state.mode === 'recurring'
    }

    source.addEventListener('state', function (e) {
      var data = JSON.parse(e.data)
      updateState(data)
    }, false)

    function loadState () {
      fetch('/state')
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
        updateState(data)
      })
      .catch(function (err) {
        console.log(err)
      })
    }

    var recurringForm = document.getElementById('recurring')
    recurringForm.addEventListener('submit', function (e) {
      e.preventDefault()
      fetch('/recurring', {
        method: 'POST',
        body: combineForms(settingsForm, recurringForm)
      })
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
      })
      .catch(function (err) {
        console.log(err)
      })
    }, false)

    var recurringStop = document.getElementById('recurring_stop')
    recurringStop.addEventListener('click', function (e) {
      e.preventDefault()
      fetch('/recurring', {
        method: 'DELETE'
      })
      .then(function (r) {
        return r.json()
      })
      .then(function (data) {
      })
      .catch(function (err) {
        console.log(err)
      })
    }, false)

    loadState()
  })
})()
