// Platform Selection Logic
function setPlatform(platformName, event) {
    document.getElementById('platform').value = platformName;

    let buttons = document.querySelectorAll('.platform-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    event.currentTarget.classList.add('active');

    let submitBtn = document.getElementById('submitBtn');
    if (platformName === 'amazon') {
        submitBtn.style.background = '#232f3e';
    } else if (platformName === 'flipkart') {
        submitBtn.style.background = '#2874f0';
    } else if (platformName === 'meesho') {
        submitBtn.style.background = '#f43397';
    }
}

// File Name Display Update
function updateFileName() {
    let fileInput = document.getElementById('fileInput');
    let fileNameDisplay = document.getElementById('fileName');

    if (fileInput.files.length > 0) {
        fileNameDisplay.innerHTML = `<span style="color: #28a745; font-weight: bold;">Selected:</span> ${fileInput.files[0].name}`;
    } else {
        fileNameDisplay.innerHTML = 'Koi file select nahi ki...';
    }
}

// Drag and Drop Logic
document.addEventListener("DOMContentLoaded", function () {
    let dropZone = document.getElementById('dropZone');
    let fileInput = document.getElementById('fileInput');

    // Jab file box ke upar aati hai
    dropZone.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    // Jab file box se bahar jati hai bina drop kiye
    dropZone.addEventListener('dragleave', function (e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
    });

    // Jab file box par drop (chhod) di jati hai
    dropZone.addEventListener('drop', function (e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        // Check agar drop ki gayi file exist karti hai
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files; // Hidden input me file set karein
            updateFileName(); // UI me naam update karein
        }
    });
});
