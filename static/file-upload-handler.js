// File Upload Handler
function renderUploadedFiles(session) {
    const container = document.getElementById('uploaded-files');
    if (!container) return;
    
    if (!session.uploadedFiles || session.uploadedFiles.length === 0) {
        container.classList.add('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    container.innerHTML = '';
    
    session.uploadedFiles.forEach((file, index) => {
        const fileChip = document.createElement('div');
        fileChip.className = 'flex items-center gap-2 px-3 py-2 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-lg text-sm border border-blue-200 dark:border-blue-800';
        
        const fileIcon = document.createElement('span');
        fileIcon.className = 'material-symbols-outlined text-base';
        fileIcon.textContent = getFileIcon(file.name);
        
        const fileName = document.createElement('span');
        fileName.className = 'max-w-[150px] truncate';
        fileName.textContent = file.name;
        
        const fileSize = document.createElement('span');
        fileSize.className = 'text-xs opacity-70';
        fileSize.textContent = formatFileSize(file.size);
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'ml-1 hover:bg-blue-200 dark:hover:bg-blue-800 rounded p-0.5 transition-colors';
        removeBtn.innerHTML = '<span class="material-symbols-outlined text-base">close</span>';
        removeBtn.onclick = () => {
            session.uploadedFiles.splice(index, 1);
            renderUploadedFiles(session);
        };
        
        fileChip.appendChild(fileIcon);
        fileChip.appendChild(fileName);
        fileChip.appendChild(fileSize);
        fileChip.appendChild(removeBtn);
        
        container.appendChild(fileChip);
    });
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const iconMap = {
        'pdf': 'picture_as_pdf',
        'doc': 'description',
        'docx': 'description',
        'txt': 'article',
        'md': 'article',
        'png': 'image',
        'jpg': 'image',
        'jpeg': 'image',
        'gif': 'image',
        'svg': 'image',
        'webp': 'image',
        'js': 'code',
        'py': 'code',
        'html': 'code',
        'css': 'code',
        'json': 'code',
        'zip': 'folder_zip',
        'rar': 'folder_zip',
        'mp3': 'audio_file',
        'mp4': 'video_file',
        'avi': 'video_file'
    };
    return iconMap[ext] || 'insert_drive_file';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
