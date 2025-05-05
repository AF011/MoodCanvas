/**
 * Mood Canvas Diary Dynamic JavaScript
 * Handles all diary operations and interaction with the backend
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const diaryList = document.getElementById('diaryList');
    const diaryDisplay = document.getElementById('diaryDisplay');
    const chatToggleBtn = document.getElementById('chatToggleBtn');
    const notepadInterface = document.getElementById('notepadInterface');
    const notepadClose = document.getElementById('notepadClose');
    const discardBtn = document.getElementById('discardBtn');
    const saveNotepadBtn = document.getElementById('saveNotepadBtn');
    const notepadContent = document.getElementById('notepadContent');
    const diaryTitle = document.getElementById('diaryTitle');
    const entryTimestamp = document.getElementById('entryTimestamp');
    const moodItems = document.querySelectorAll('.mood-item');
    const deleteModal = document.getElementById('deleteModal');
    const cancelDelete = document.getElementById('cancelDelete');
    const confirmDelete = document.getElementById('confirmDelete');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const saveBtn = document.getElementById('saveBtn');
    const clearBtn = document.getElementById('clearBtn');
    const toast = document.getElementById('toast');
    
    // Global variables
    let currentEntryId = null;
    let currentMood = 'neutral';
    let isEditing = false;
    let selectedEntryForDeletion = null;
    
    // Set current date in the header
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = now.toLocaleDateString('en-US', options);
    
    // Initialize diary by loading entries
    loadEntries();
    
    // Notepad Interface Functions
    
    // Open notepad for new entry
    chatToggleBtn.addEventListener('click', function() {
        isEditing = false;
        currentEntryId = null;
        this.classList.add('active');
        notepadInterface.style.display = 'flex';
        notepadContent.innerHTML = '';
        notepadContent.focus();
    });
    
    // Close notepad
    function closeNotepad() {
        notepadInterface.style.display = 'none';
        chatToggleBtn.classList.remove('active');
        notepadContent.innerHTML = '';
    }
    
    notepadClose.addEventListener('click', closeNotepad);
    discardBtn.addEventListener('click', closeNotepad);
    
    // Save notepad content as a new entry
    saveNotepadBtn.addEventListener('click', function() {
        const content = notepadContent.innerHTML;
        
        if (!content.trim()) {
            showToast('Please write something before saving', 'error');
            return;
        }
        
        if (isEditing && currentEntryId) {
            // Update existing entry
            updateEntry(currentEntryId, {
                content: content
            });
        } else {
            // Create new entry
            createEntry(
                diaryTitle.value || 'Untitled Entry',
                content,
                currentMood
            );
        }
        
        closeNotepad();
    });
    
    // Diary CRUD Operations
    
    // Load diary entries from server
    function loadEntries() {
        fetch('/smart_diary/entries')
            .then(response => response.json())
            .then(data => {
                if (data.entries && data.entries.length > 0) {
                    renderEntryList(data.entries);
                    // Load the first entry
                    loadEntry(data.entries[0].id);
                } else {
                    // Empty state
                    diaryList.innerHTML = '<div class="no-entries">No entries yet. Click the button below to create your first diary entry.</div>';
                    diaryDisplay.innerHTML = '';
                    entryTimestamp.textContent = '';
                    diaryTitle.value = '';
                }
            })
            .catch(error => {
                console.error('Error loading entries:', error);
                showToast('Failed to load diary entries', 'error');
            });
    }
    
    // Render the list of entries in the sidebar
    function renderEntryList(entries) {
        diaryList.innerHTML = '';
        
        entries.forEach(entry => {
            const entryDate = new Date(entry.created_at);
            const dateFormatted = entryDate.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
            
            const timeFormatted = entryDate.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            // Truncate content for preview
            let contentPreview = entry.content;
            // Strip HTML tags
            contentPreview = contentPreview.replace(/<[^>]*>/g, '');
            // Limit to 80 characters
            contentPreview = contentPreview.length > 80 ? 
                contentPreview.substring(0, 80) + '...' : 
                contentPreview;
                
            const entryElement = document.createElement('div');
            entryElement.className = 'diary-entry';
            entryElement.setAttribute('data-id', entry.id);
            
            // Show indicator icon if entry has AI response
            const aiIndicator = entry.has_ai_response ? '<i class="fas fa-comment-dots"></i>' : '';
            
            // Like button status
            const likeButtonClass = entry.liked ? 'active' : '';
            const likeButtonIcon = entry.liked ? '<i class="fas fa-heart"></i>' : '<i class="far fa-heart"></i>';
            
            // Create the markup for the entry
            entryElement.innerHTML = `
                <div class="corner-fold"></div>
                <h3>${entry.title} ${aiIndicator}</h3>
                <span class="entry-time">${dateFormatted} - ${timeFormatted}</span>
                <div class="entry-content">${contentPreview}</div>
                <div class="entry-actions">
                    <button class="entry-btn like-btn ${likeButtonClass}" data-id="${entry.id}">${likeButtonIcon}</button>
                    <button class="entry-btn delete-btn" data-id="${entry.id}"><i class="far fa-trash-alt"></i></button>
                </div>
            `;
            
            // Add click event to load this entry
            entryElement.addEventListener('click', function() {
                // Toggle the expanded class
                this.classList.toggle('expanded');
                // Load the entry content
                loadEntry(entry.id);
            });
            
            diaryList.appendChild(entryElement);
        });
        
        // Add event listeners for like and delete buttons
        setupEntryButtons();
    }
    
    // Set up event listeners for entry buttons
    function setupEntryButtons() {
        // Like buttons
        const likeButtons = document.querySelectorAll('.like-btn');
        likeButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent entry expansion
                const entryId = this.getAttribute('data-id');
                toggleLike(entryId);
            });
        });
        
        // Delete buttons
        const deleteButtons = document.querySelectorAll('.delete-btn');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent entry expansion
                const entryId = this.closest('.diary-entry').getAttribute('data-id');
                showDeleteConfirmation(entryId);
            });
        });
    }
    
    // Load a specific entry
    function loadEntry(entryId) {
        currentEntryId = entryId;
        
        fetch(`/smart_diary/entry/${entryId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load entry');
                }
                return response.json();
            })
            .then(data => {
                if (data.entry) {
                    displayEntry(data.entry);
                }
            })
            .catch(error => {
                console.error('Error loading entry:', error);
                showToast('Failed to load diary entry', 'error');
            });
    }
    
    // Display an entry in the main content area
    function displayEntry(entry) {
        // Set title and timestamp
        diaryTitle.value = entry.title;
        
        const entryDate = new Date(entry.created_at);
        entryTimestamp.textContent = entryDate.toLocaleDateString('en-US', { 
            weekday: 'long',
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        }) + ' - ' + entryDate.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // Set mood
        moodItems.forEach(item => {
            if (item.getAttribute('data-mood') === entry.mood) {
                item.classList.add('selected');
                currentMood = entry.mood;
            } else {
                item.classList.remove('selected');
            }
        });
        
        // Clear display
        diaryDisplay.innerHTML = '';
        
        // Display the main entry content
        const messageWrapper = document.createElement('div');
        messageWrapper.className = 'message-wrapper user-message';
        
        const timestamp = document.createElement('span');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = entryDate.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = entry.content;
        
        messageWrapper.appendChild(timestamp);
        messageWrapper.appendChild(messageContent);
        diaryDisplay.appendChild(messageWrapper);
        
        // Display conversation messages if any
        if (entry.messages && entry.messages.length > 0) {
            entry.messages.forEach(msg => {
                if (msg.sender === 'user' && msg.content.trim() !== entry.content.trim()) {
                    // Only show additional user messages (not the main entry content)
                    addMessageToDisplay('user', msg.content, new Date(msg.timestamp));
                } else if (msg.sender === 'alter_ego') {
                    addMessageToDisplay('alter_ego', msg.content, new Date(msg.timestamp));
                }
            });
        }
        
        // Scroll to bottom
        diaryDisplay.scrollTop = diaryDisplay.scrollHeight;
        
        // Show chat interface
        document.querySelector('.chat-interface').style.display = 'flex';
    }
    
    // Create a new entry
    function createEntry(title, content, mood) {
        const entryData = {
            title: title,
            content: content,
            mood: mood
        };
        
        fetch('/smart_diary/entry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(entryData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to create entry');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showToast('Entry saved successfully!');
                // Reload entries to show the new one
                loadEntries();
                
                // If there was an alter ego response, load the entry to show it
                if (data.alter_ego_response) {
                    setTimeout(() => {
                        loadEntry(data.entry_id);
                    }, 500);
                }
            }
        })
        .catch(error => {
            console.error('Error creating entry:', error);
            showToast('Failed to save entry', 'error');
        });
    }
    
    // Update an existing entry
    function updateEntry(entryId, updateData) {
        fetch(`/smart_diary/entry/${entryId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to update entry');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showToast('Entry updated successfully!');
                
                // Reload the entry to refresh content
                loadEntry(entryId);
                
                // Reload entry list to reflect changes
                loadEntries();
                
                // If there was a new alter ego response, it will show when we reload the entry
            }
        })
        .catch(error => {
            console.error('Error updating entry:', error);
            showToast('Failed to update entry', 'error');
        });
    }
    
    // Delete an entry
    function deleteEntry(entryId) {
        fetch(`/smart_diary/entry/${entryId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to delete entry');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showToast('Entry deleted successfully!');
                
                // Clear current display if we deleted the current entry
                if (entryId === currentEntryId) {
                    diaryDisplay.innerHTML = '';
                    entryTimestamp.textContent = '';
                    diaryTitle.value = '';
                    document.querySelector('.chat-interface').style.display = 'none';
                    currentEntryId = null;
                }
                
                // Reload entries to update the list
                loadEntries();
            }
        })
        .catch(error => {
            console.error('Error deleting entry:', error);
            showToast('Failed to delete entry', 'error');
        });
    }
    
    // Toggle like status for an entry
    function toggleLike(entryId) {
        fetch(`/smart_diary/entry/${entryId}/like`, {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to update like status');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update like button appearance in the list
                const likeBtn = document.querySelector(`.like-btn[data-id="${entryId}"]`);
                if (likeBtn) {
                    if (data.liked) {
                        likeBtn.classList.add('active');
                        likeBtn.innerHTML = '<i class="fas fa-heart"></i>';
                    } else {
                        likeBtn.classList.remove('active');
                        likeBtn.innerHTML = '<i class="far fa-heart"></i>';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error toggling like:', error);
            showToast('Failed to update like status', 'error');
        });
    }
    
    // Send a message in the diary conversation
    function sendMessage() {
        if (!currentEntryId) {
            showToast('Please select an entry first', 'error');
            return;
        }
        
        const message = chatInput.value.trim();
        if (!message) {
            return;
        }
        
        // Add user message to display immediately
        addMessageToDisplay('user', message);
        
        // Clear input
        chatInput.value = '';
        
        // Show thinking indicator
        const thinkingIndicator = document.createElement('div');
        thinkingIndicator.className = 'thinking-indicator';
        thinkingIndicator.innerHTML = '<span></span><span></span><span></span>';
        diaryDisplay.appendChild(thinkingIndicator);
        diaryDisplay.scrollTop = diaryDisplay.scrollHeight;
        
        // Send to server
        fetch(`/smart_diary/entry/${currentEntryId}/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to send message');
            }
            return response.json();
        })
        .then(data => {
            // Remove thinking indicator
            const indicator = document.querySelector('.thinking-indicator');
            if (indicator) {
                diaryDisplay.removeChild(indicator);
            }
            
            if (data.success && data.response) {
                // Add alter ego response to display
                addMessageToDisplay('alter_ego', data.response);
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            
            // Remove thinking indicator
            const indicator = document.querySelector('.thinking-indicator');
            if (indicator) {
                diaryDisplay.removeChild(indicator);
            }
            
            showToast('Failed to send message', 'error');
        });
    }
    
    // Add a message to the diary display
    function addMessageToDisplay(sender, content, timestamp = new Date()) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `message-wrapper ${sender === 'user' ? 'user-message' : 'alter-ego-message'}`;
        
        const timestampElem = document.createElement('span');
        timestampElem.className = 'message-timestamp';
        timestampElem.textContent = timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = content;
        
        messageWrapper.appendChild(timestampElem);
        messageWrapper.appendChild(messageContent);
        diaryDisplay.appendChild(messageWrapper);
        
        // Auto scroll to bottom
        diaryDisplay.scrollTop = diaryDisplay.scrollHeight;
    }
    
    // Show delete confirmation modal
    function showDeleteConfirmation(entryId) {
        selectedEntryForDeletion = entryId;
        deleteModal.style.display = 'flex';
    }
    
    // UI Helpers
    
    // Show toast notification
    function showToast(message, type = 'success') {
        toast.textContent = message;
        toast.className = 'toast ' + type;
        toast.style.opacity = '1';
        
        setTimeout(() => {
            toast.style.opacity = '0';
        }, 3000);
    }
    
    // Edit the current entry
    function editCurrentEntry() {
        if (!currentEntryId) {
            showToast('No entry selected', 'error');
            return;
        }
        
        // Get the current entry content
        fetch(`/smart_diary/entry/${currentEntryId}`)
            .then(response => response.json())
            .then(data => {
                if (data.entry) {
                    // Open notepad with current content
                    isEditing = true;
                    notepadInterface.style.display = 'flex';
                    chatToggleBtn.classList.add('active');
                    notepadContent.innerHTML = data.entry.content;
                    notepadContent.focus();
                }
            })
            .catch(error => {
                console.error('Error loading entry for edit:', error);
                showToast('Failed to load entry for editing', 'error');
            });
    }
    
    // Event Listeners
    
    // Save button
    saveBtn.addEventListener('click', function() {
        if (!currentEntryId) {
            showToast('No entry selected', 'error');
            return;
        }
        
        // Update the entry title and mood
        updateEntry(currentEntryId, {
            title: diaryTitle.value,
            mood: currentMood
        });
    });
    
    // Clear button
    clearBtn.addEventListener('click', function() {
        // Clear diary display and input
        diaryDisplay.innerHTML = '';
        diaryTitle.value = '';
        chatInput.value = '';
        
        // Reset mood selection
        moodItems.forEach(item => item.classList.remove('selected'));
        currentMood = 'neutral';
        
        // Hide chat interface
        document.querySelector('.chat-interface').style.display = 'none';
        
        // Reset current entry
        currentEntryId = null;
    });
    
    // Chat input and send button
    sendBtn.addEventListener('click', sendMessage);
    
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Mood selection
    moodItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove selected class from all mood items
            moodItems.forEach(i => i.classList.remove('selected'));
            
            // Add selected class to clicked item
            this.classList.add('selected');
            
            // Update current mood
            currentMood = this.getAttribute('data-mood');
            
            // If we have a current entry, update its mood
            if (currentEntryId) {
                updateEntry(currentEntryId, { mood: currentMood });
            }
        });
    });
    
    // Delete confirmation
    cancelDelete.addEventListener('click', function() {
        deleteModal.style.display = 'none';
        selectedEntryForDeletion = null;
    });
    
    confirmDelete.addEventListener('click', function() {
        if (selectedEntryForDeletion) {
            deleteEntry(selectedEntryForDeletion);
            deleteModal.style.display = 'none';
            selectedEntryForDeletion = null;
        }
    });
    
    // Title input change
    diaryTitle.addEventListener('change', function() {
        if (currentEntryId) {
            updateEntry(currentEntryId, { title: this.value });
        }
    });
    
    // Add double click on diary display to edit
    diaryDisplay.addEventListener('dblclick', function(e) {
        // Only if clicked on user message content
        if (e.target.closest('.user-message')) {
            editCurrentEntry();
        }
    });
});