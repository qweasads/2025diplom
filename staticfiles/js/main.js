document.addEventListener('DOMContentLoaded', function() {
    // Обработка сообщений
    const messages = document.querySelectorAll('.message');
    messages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });

    // Обработка вкладок
    const tabs = document.querySelectorAll('.tab');
    if (tabs.length > 0) {
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Удаляем активный класс со всех вкладок
                tabs.forEach(t => t.classList.remove('active'));
                // Добавляем активный класс на текущую вкладку
                this.classList.add('active');
                
                // Скрываем все содержимое вкладок
                const tabContents = document.querySelectorAll('.tab-content');
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Показываем содержимое текущей вкладки
                const tabId = this.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }

    // Обработка загрузки файлов
    const fileInput = document.getElementById('file-upload');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileList = document.querySelector('.file-list');
            fileList.innerHTML = '';
            
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                
                // Определяем иконку в зависимости от типа файла
                let iconClass = 'fa-file';
                if (file.type.startsWith('image/')) {
                    iconClass = 'fa-file-image';
                } else if (file.type === 'application/pdf') {
                    iconClass = 'fa-file-pdf';
                } else if (file.type.includes('word')) {
                    iconClass = 'fa-file-word';
                } else if (file.type.includes('excel') || file.type.includes('spreadsheet')) {
                    iconClass = 'fa-file-excel';
                }
                
                fileItem.innerHTML = `
                    <i class="fas ${iconClass}"></i>
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">(${formatFileSize(file.size)})</span>
                    <div class="file-actions">
                        <a href="#" class="remove-file"><i class="fas fa-times"></i></a>
                    </div>
                `;
                
                fileList.appendChild(fileItem);
            }
            
            // Обработка удаления файла
            const removeButtons = document.querySelectorAll('.remove-file');
            removeButtons.forEach(button => {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    this.closest('.file-item').remove();
                });
            });
        });
    }

    // Функция форматирования размера файла
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Байт';
        const k = 1024;
        const sizes = ['Байт', 'КБ', 'МБ', 'ГБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Обработка формы создания тикета
    const ticketForm = document.getElementById('ticket-form');
    if (ticketForm) {
        ticketForm.addEventListener('submit', function(e) {
            const title = document.getElementById('title').value.trim();
            const category = document.getElementById('category').value;
            const description = document.getElementById('description').value.trim();
            
            if (!title || !description) {
                e.preventDefault();
                alert('Пожалуйста, заполните все обязательные поля');
            }
        });
    }

    // Обработка формы ответа на тикет
    const replyForm = document.getElementById('reply-form');
    if (replyForm) {
        replyForm.addEventListener('submit', function(e) {
            const message = document.getElementById('message').value.trim();
            
            if (!message) {
                e.preventDefault();
                alert('Пожалуйста, введите сообщение');
            }
        });
    }

    // Обработка изменения статуса тикета
    const statusSelect = document.getElementById('status-select');
    if (statusSelect) {
        statusSelect.addEventListener('change', function() {
            const ticketId = this.getAttribute('data-ticket-id');
            const status = this.value;
            
            fetch(`/api/tickets/${ticketId}/status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ status: status })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Обновляем статус на странице
                    const statusBadge = document.querySelector('.ticket-status');
                    statusBadge.textContent = getStatusText(status);
                    statusBadge.className = `status status-${status}`;
                    
                    // Показываем сообщение об успехе
                    showMessage('Статус тикета успешно обновлен', 'success');
                } else {
                    showMessage('Ошибка при обновлении статуса', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('Произошла ошибка при обновлении статуса', 'error');
            });
        });
    }

    // Функция получения текста статуса
    function getStatusText(status) {
        switch (status) {
            case 'open':
                return 'Открыт';
            case 'in-progress':
                return 'В процессе';
            case 'closed':
                return 'Закрыт';
            default:
                return 'Неизвестно';
        }
    }

    // Функция для получения значения cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Функция для отображения сообщения
    function showMessage(text, type) {
        const messagesContainer = document.querySelector('.messages');
        if (!messagesContainer) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = text;
        
        messagesContainer.appendChild(messageElement);
        
        setTimeout(() => {
            messageElement.style.opacity = '0';
            setTimeout(() => {
                messageElement.remove();
            }, 500);
        }, 5000);
    }

    // Поиск и фильтрация тикетов
    const searchInput = document.getElementById('search-tickets');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tickets = document.querySelectorAll('.ticket-item');
            
            tickets.forEach(ticket => {
                const title = ticket.querySelector('.ticket-title').textContent.toLowerCase();
                const id = ticket.querySelector('.ticket-id').textContent.toLowerCase();
                const category = ticket.querySelector('.ticket-category').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || id.includes(searchTerm) || category.includes(searchTerm)) {
                    ticket.style.display = '';
                } else {
                    ticket.style.display = 'none';
                }
            });
        });
    }

    // Фильтрация по статусу
    const statusFilters = document.querySelectorAll('.status-filter');
    if (statusFilters.length > 0) {
        statusFilters.forEach(filter => {
            filter.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Удаляем активный класс со всех фильтров
                statusFilters.forEach(f => f.classList.remove('active'));
                // Добавляем активный класс на текущий фильтр
                this.classList.add('active');
                
                const status = this.getAttribute('data-status');
                const tickets = document.querySelectorAll('.ticket-item');
                
                tickets.forEach(ticket => {
                    if (status === 'all' || ticket.getAttribute('data-status') === status) {
                        ticket.style.display = '';
                    } else {
                        ticket.style.display = 'none';
                    }
                });
            });
        });
    }

    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    function updateIcon() {
        if (document.body.classList.contains('dark-theme')) {
            themeIcon.className = 'fas fa-sun';
        } else {
            themeIcon.className = 'fas fa-moon';
        }
    }
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-theme');
    }
    updateIcon();
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
            updateIcon();
        });
    }
});