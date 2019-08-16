// Override default file upload

function handleForm(event) {
    event.preventDefault();
    files = []
    for (var i = 0; i < event.target[0].files.length; i++) {
        files.push(event.target[0].files[i])
    }
    if (event.srcElement.id === 'audioForm') {
        files.forEach((file) => uploadFile(file, file['name'], 'audio'))
    } else if (event.srcElement.id === 'textForm') {
        files.forEach((file) => uploadFile(file, file['name'], 'text'))
    } else if (event.srcElement.id === 'mapForm') {
        files.forEach((file) => uploadFile(file, file['name'], 'mapping'))
    }
}

try {
    document.getElementById('audioForm').addEventListener('submit', handleForm)
    document.getElementById('textForm').addEventListener('submit', handleForm)
    document.getElementById('mapForm').addEventListener('submit', handleForm)
} catch (error) {
    console.warn("forms not found, this is fine if you're not on step 1, otherwise it's an error.")
}

// Toastr settings
toastr.options = {
    "closeButton": false,
    "debug": false,
    "newestOnTop": false,
    "progressBar": false,
    "positionClass": "toast-top-right",
    "preventDuplicates": false,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "5000",
    "extendedTimeOut": "1000",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
  }


// File Management Socket

var file_socket = io.connect('http://' + document.domain + ':' + location.port + '/file');

function uploadFile(file, name, type) {
    file_socket.emit('upload event', { data: { 'file': file }, name: name, type: type })
}

file_socket.on('upload response', function (msg) {
    toastr["success"](`File '${msg['data']['path'].split('/').pop()}' Uploaded!`)
})

function removeFile(path) {
    let host_path = path[0]['path'];
    file_socket.emit('remove event', { data: { 'path_to_remove': host_path } })
}

file_socket.on('remove response', function (msg) {
    let element = document.getElementById(msg['data']['removed_file'])
    element.parentNode.removeChild(element)
})

// Readalongs Configuration Socket

var config_socket = io.connect('http://' + document.domain + ':' + location.port + '/config')

function updateConfig(k, v) {
    const data_obj = {}
    data_obj[k] = v
    config_socket.emit('config update event', data_obj )
}

config_socket.on('config update response', function (msg) {
    if (!msg.hasOwnProperty('error')){
        toastr["success"](`Configuration updated!`)
    } else {
        toastr["error"](`Hmm. Something went wrong. Please try again. ${msg['error']}`)
    }
   
})

// Spinner
function spinner(id) {
    document.getElementById(id).classList.add('is-active')
}

