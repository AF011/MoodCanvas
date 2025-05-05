// Current date formatting
function formatDate(date, format = 'long') {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }

    const day = date.getDate();
    const month = date.getMonth();
    const year = date.getFullYear();
    
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    const monthShort = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    
    if (format === 'long') {
        return `${monthNames[month]} ${day}, ${year}`;
    } else if (format === 'short') {
        return `${monthShort[month]} ${day}, ${year}`;
    } else if (format === 'time') {
        const hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const formattedHours = hours % 12 || 12;
        const formattedMinutes = minutes < 10 ? '0' + minutes : minutes;
        return `${formattedHours}:${formattedMinutes} ${ampm}`;
    } else if (format === 'datetime') {
        const hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const formattedHours = hours % 12 || 12;
        const formattedMinutes = minutes < 10 ? '0' + minutes : minutes;
        return `${monthShort[month]} ${day}, ${year} at ${formattedHours}:${formattedMinutes} ${ampm}`;
    }
}

// Set current date
const today = new Date();
document.getElementById('currentDate').textContent = formatDate(today);

// Global variables
let diaryEntries = [];
let currentEditingId = null;
let entryToDelete = null;
let currentEntryDate = new Date();
let currentImageFile = null;
let pendingUpload = false;
let alterEgoEnabled = true; // Default to enabled
let alterEgoPersonality = 'reflective'; // Default personality
let isGeneratingResponse = false; // Track if we're waiting for an AI response

// DOM Elements
const diaryList = document.getElementById('diaryList');
const diaryTitle = document.getElementById('diaryTitle');
const diaryDisplay = document.getElementById('diaryDisplay');
const entryTimestamp = document.getElementById('entryTimestamp');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');
const deleteModal = document.getElementById('deleteModal');
const cancelDelete = document.getElementById('cancelDelete');
const confirmDelete = document.getElementById('confirmDelete');
const newEntryBtn = document.getElementById('newEntryBtn');
const typingPreview = document.getElementById('typingPreview');
const moodItems = document.querySelectorAll('.mood-item');
const formatTextBtn = document.getElementById('formatTextBtn');
const addDateBtn = document.getElementById('addDateBtn');
const imageUpload = document.getElementById('imageUpload');
const fileUpload = document.getElementById('fileUpload');
const alterEgoToggle = document.getElementById('alterEgoToggle');
const personalitySelector = document.getElementById('personalitySelector');

// Load diary entries from the API
async function loadEntries() {
    try {
        const response = await fetch('/api/entries');
        if (!response.ok) {
            throw new Error('Failed to load entries');
        }
        
        diaryEntries = await response.json();
        renderDiaryEntries();
    } catch (error) {
        console.error('Error loading entries:', error);
        showToast('Failed to load diary entries. Please try again.', 'error');
    }
}

// Render diary entries in the sidebar
function renderDiaryEntries() {
    diaryList.innerHTML = '';
    
    if (diaryEntries.length === 0) {
        diaryList.innerHTML = '<div class="no-entries">No entries yet. Create your first one!</div>';
        return;
    }
    
    // Sort entries by date (newest first)
    const sortedEntries = [...diaryEntries].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    sortedEntries.forEach(entry => {
        const entryElement = document.createElement('div');
        entryElement.className = 'diary-entry';
        entryElement.dataset.id = entry.id;
        
        // Format entry date
        const entryDate = new Date(entry.date);
        const dateFormatted = formatDate(entryDate, 'short');
        const timeFormatted = formatDate(entryDate, 'time');
        
        // Get mood emoji
        let moodEmoji = "📝";
        switch(entry.mood) {
            case 'happy': moodEmoji = "😊"; break;
            case 'sad': moodEmoji = "😢"; break;
            case 'excited': moodEmoji = "😃"; break;
            case 'angry': moodEmoji = "😠"; break;
            case 'neutral': moodEmoji = "😐"; break;
        }
        
        // Truncate content for preview - remove HTML tags and get plain text
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = entry.content;
        const plainText = tempDiv.textContent || tempDiv.innerText || '';
        const contentPreview = plainText.slice(0, 100) + (plainText.length > 100 ? '...' : '');
        
        // Check if entry has images
        const hasImages = entry.content.includes('<img');
        const imageIndicator = hasImages ? '<i class="fas fa-image" style="margin-left: 5px; color: var(--highlight-color);"></i>' : '';
        
        // Check if entry has alter ego responses
        const hasAlterEgo = entry.has_alter_ego_response;
        const alterEgoIndicator = hasAlterEgo ? '<i class="fas fa-comment-dots" style="margin-left: 5px; color: var(--highlight-color);"></i>' : '';
        
        // Create the HTML structure
        entryElement.innerHTML = `
            <div class="corner-fold"></div>
            <h3>
                <span>${entry.title} ${moodEmoji} ${imageIndicator} ${alterEgoIndicator}</span>
            </h3>
            <div class="entry-time">${dateFormatted} - ${timeFormatted}</div>
            <div class="entry-content">${contentPreview}</div>
            <div class="entry-actions">
                <button class="entry-btn edit-btn" title="Edit"><i class="fas fa-edit"></i></button>
                <button class="entry-btn like-btn ${entry.liked ? 'active' : ''}" title="${entry.liked ? 'Unlike' : 'Like'}">
                    <i class="fas fa-heart"></i>
                </button>
                <button class="entry-btn delete-btn" title="Delete"><i class="fas fa-trash"></i></button>
            </div>
        `;
        
        // Add click event to toggle expanded view
        entryElement.querySelector('h3').addEventListener('click', (e) => {
            // Only toggle if clicking on the title, not the buttons
            if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
                entryElement.classList.toggle('expanded');
            }
        });
        
        // Add click events for buttons
        entryElement.querySelector('.edit-btn').addEventListener('click', () => {
            loadDiaryEntry(entry.id);
        });
        
        entryElement.querySelector('.like-btn').addEventListener('click', () => {
            toggleLike(entry.id);
        });
        
        entryElement.querySelector('.delete-btn').addEventListener('click', () => {
            showDeleteModal(entry.id);
        });
        
        diaryList.appendChild(entryElement);
    });
}

// Load diary entry to edit
function loadDiaryEntry(id) {
    const entry = diaryEntries.find(entry => entry.id === id);
    if (entry) {
        // Save current scroll position
        const scrollPos = window.scrollY;
        
        diaryTitle.value = entry.title;
        diaryDisplay.innerHTML = entry.content;
        chatInput.value = '';
        
        // Set current entry date
        currentEntryDate = new Date(entry.date);
        
        // Update timestamp
        updateEntryTimestamp();
        
        // Select mood
        moodItems.forEach(item => {
            item.classList.remove('selected');
            if (item.dataset.mood === entry.mood) {
                item.classList.add('selected');
            }
        });
        
        // Update current editing ID
        currentEditingId = id;
        
        // Change save button text
        saveBtn.textContent = 'Update Entry';
        
        // Load conversation messages if this entry has alter ego responses
        if (entry.has_alter_ego_response) {
            loadConversationMessages(id);
        }
        
        // Smooth scroll to editor on mobile, maintain position on desktop
        if (window.innerWidth <= 768) {
            document.querySelector('.main-content').scrollIntoView({ behavior: 'smooth' });
        } else {
            // Restore scroll position with a slight delay to avoid jumps
            setTimeout(() => {
                window.scrollTo({
                    top: scrollPos,
                    behavior: 'auto'
                });
            }, 10);
        }
    }
}

// Load conversation messages for an entry
async function loadConversationMessages(entryId) {
    try {
        const response = await fetch(`/api/entries/${entryId}/messages`);
        if (!response.ok) {
            throw new Error('Failed to load messages');
        }
        
        const result = await response.json();
        if (result.success && result.messages && result.messages.length > 0) {
            // Clear any existing content
            diaryDisplay.innerHTML = '';
            
            // Add each message to the display
            result.messages.forEach(message => {
                if (message.is_user) {
                    addUserMessageToDisplay(message.content);
                } else {
                    addAlterEgoMessageToDisplay(message.content);
                }
            });
            
            // Scroll to the bottom
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'auto'
            });
        }
    } catch (error) {
        console.error('Error loading conversation messages:', error);
        showToast('Failed to load conversation. Please try again.', 'error');
    }
}

// Update entry timestamp display
function updateEntryTimestamp() {
    const formattedDate = formatDate(currentEntryDate, 'datetime');
    entryTimestamp.textContent = `Last edited: ${formattedDate}`;
}

// Show delete confirmation modal
function showDeleteModal(id) {
    entryToDelete = id;
    deleteModal.style.display = 'flex';
}

// Close delete confirmation modal
function closeDeleteModal() {
    deleteModal.style.display = 'none';
    entryToDelete = null;
}

// Delete diary entry
async function deleteEntry(id) {
    try {
        const response = await fetch(`/api/entries/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete entry');
        }
        
        // If currently editing this entry, reset the form
        if (currentEditingId === id) {
            resetForm();
        }
        
        // Filter out the deleted entry
        diaryEntries = diaryEntries.filter(entry => entry.id !== id);
        
        // Re-render entries
        renderDiaryEntries();
        
        // Show confirmation toast
        showToast('Entry deleted successfully');
    } catch (error) {
        console.error('Error deleting entry:', error);
        showToast('Failed to delete entry. Please try again.', 'error');
    }
}

// Toggle like for an entry
async function toggleLike(id) {
    try {
        const response = await fetch(`/api/entries/${id}/like`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to update like status');
        }
        
        const result = await response.json();
        
        // Update the entry in the local array
        const entryIndex = diaryEntries.findIndex(entry => entry.id === id);
        if (entryIndex !== -1) {
            diaryEntries[entryIndex].liked = result.liked;
        }
        
        // Re-render entries
        renderDiaryEntries();
        
        // Show confirmation toast
        if (result.liked) {
            showToast('Added to favorites');
        } else {
            showToast('Removed from favorites');
        }
    } catch (error) {
        console.error('Error toggling like:', error);
        showToast('Failed to update like status. Please try again.', 'error');
    }
}

// Upload image
async function uploadImage(file) {
    try {
        const formData = new FormData();
        formData.append('image', file);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload image');
        }
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error uploading image:', error);
        showToast('Failed to upload image. Please try again.', 'error');
        return null;
    }
}

// Upload image from data URL
async function uploadImageFromDataUrl(dataUrl) {
    try {
        const formData = new FormData();
        formData.append('image', dataUrl);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload image');
        }
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error uploading image:', error);
        showToast('Failed to upload image. Please try again.', 'error');
        return null;
    }
}

// Add user message to display
function addUserMessageToDisplay(content) {
    // Create message wrapper for user message (left side)
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper user-message';
    
    // Get current time
    const now = new Date();
    const timeFormatted = formatDate(now, 'time');
    
    // Create a timestamp element
    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = timeFormatted;
    messageWrapper.appendChild(timestamp);
    
    // Add the content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = content;
    messageWrapper.appendChild(messageContent);
    
    // Add to display
    diaryDisplay.appendChild(messageWrapper);
    
    // Scroll to the bottom
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    });
}

// Add alter ego message to display
function addAlterEgoMessageToDisplay(content) {
    // Create message wrapper for alter ego (right side)
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper alter-ego-message';
    
    // Get current time
    const now = new Date();
    const timeFormatted = formatDate(now, 'time');
    
    // Create a timestamp element
    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = timeFormatted;
    messageWrapper.appendChild(timestamp);
    
    // Add the content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    messageWrapper.appendChild(messageContent);
    
    // Add to display
    diaryDisplay.appendChild(messageWrapper);
    
    // Scroll to the bottom
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    });
}


// Show alter ego thinking indicator
function showAlterEgoThinking() {
    // Create message wrapper for alter ego (right side)
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper alter-ego-message thinking';
    messageWrapper.id = 'alterEgoThinking';
    
    // Create thinking indicator
    const thinkingIndicator = document.createElement('div');
    thinkingIndicator.className = 'thinking-indicator';
    thinkingIndicator.innerHTML = '<span></span><span></span><span></span>';
    messageWrapper.appendChild(thinkingIndicator);
    
    // Add to display
    diaryDisplay.appendChild(messageWrapper);
    
    // Scroll to the bottom
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    });
}

// Remove alter ego thinking indicator
function hideAlterEgoThinking() {
    const thinkingElement = document.getElementById('alterEgoThinking');
    if (thinkingElement) {
        thinkingElement.remove();
    }
}


console.log("Debug - current values:", {
    currentEditingId: currentEditingId,
    alterEgoEnabled: alterEgoEnabled,
    isGeneratingResponse: isGeneratingResponse
});
// Update the generateAlterEgoResponse function
// Generate alter ego response
async function generateAlterEgoResponse(message) {
    console.log("generateAlterEgoResponse called", {
        currentEditingId,
        messageLength: message ? message.length : 0
    });
    
    if (!currentEditingId || isGeneratingResponse) {
        console.log("Skipping alter ego response generation - no entry ID or already generating");
        
        // If there's no current entry ID, create one
        if (!currentEditingId) {
            try {
                console.log("No current entry ID, creating a new entry first");
                // Create a new entry first
                const title = diaryTitle.value || 'Untitled Entry';
                const content = diaryDisplay.innerHTML;
                const moodElement = document.querySelector('.mood-item.selected');
                const mood = moodElement ? moodElement.dataset.mood : 'neutral';
                
                const response = await fetch('/api/entries', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        title,
                        content,
                        mood
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to create entry');
                }
                
                const result = await response.json();
                
                // Set the current ID to the new entry
                currentEditingId = result.entry.id;
                console.log("Created new entry with ID:", currentEditingId);
                
                // Now try again
                setTimeout(() => {
                    generateAlterEgoResponse(message);
                }, 100);
                return;
            } catch (error) {
                console.error('Error creating entry:', error);
                showToast('Could not create entry for alter ego response.', 'error');
                return;
            }
        }
        
        return;
    }
    
    try {
        isGeneratingResponse = true;
        console.log("Starting to generate alter ego response");
        
        // Show thinking indicator
        showAlterEgoThinking();
        
        console.log("Sending request to API", {
            entry_id: currentEditingId,
            messageLength: message.length
        });
        
        // Call API to generate response
        const response = await fetch('/api/generate-response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                entry_id: currentEditingId,
                message: message
            })
        });
        
        console.log("API response received", {
            status: response.status,
            ok: response.ok
        });
        
        // Hide thinking indicator
        hideAlterEgoThinking();
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error("API error response:", errorText);
            throw new Error(`Failed to generate alter ego response: ${response.status} ${errorText}`);
        }
        
        const result = await response.json();
        console.log("API result", result);
        
        if (result.success) {
            // Add the AI response to the display
            addAlterEgoMessageToDisplay(result.response);
            
            // Update the local entry to show it has an alter ego response
            const entryIndex = diaryEntries.findIndex(entry => entry.id === currentEditingId);
            if (entryIndex !== -1) {
                diaryEntries[entryIndex].has_alter_ego_response = true;
            }
            
            // Re-render entries to show the alter ego indicator
            renderDiaryEntries();
        } else {
            throw new Error(result.error || 'Unknown error generating response');
        }
    } catch (error) {
        console.error('Error generating alter ego response:', error);
        showToast('Could not generate alter ego response. Please try again.', 'error');
    } finally {
        isGeneratingResponse = false;
    }
}

// Add text from chat input to diary display
async function addTextToDiary() {
    console.log("addTextToDiary called");
    const text = chatInput.value.trim();
    
    if (!text && !pendingUpload) {
        console.log("No text and no pending upload, skipping");
        return; // Don't add empty messages
    }
    
    // Create message wrapper
    const messageWrapper = document.createElement('div');
    messageWrapper.className = 'message-wrapper user-message';
    
    // Get current time
    const now = new Date();
    const timeFormatted = formatDate(now, 'time');
    
    // Create a timestamp element
    const timestamp = document.createElement('div');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = timeFormatted;
    messageWrapper.appendChild(timestamp);
    
    // Create content container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    messageWrapper.appendChild(contentDiv);
    
    // Handle image upload if there's a pending one
    if (pendingUpload && currentImageFile) {
        try {
            // Show uploading indicator
            const loadingMsg = document.createElement('div');
            loadingMsg.textContent = 'Uploading image...';
            loadingMsg.className = 'image-upload-status';
            contentDiv.appendChild(loadingMsg);
            
            // Add to display temporarily
            diaryDisplay.appendChild(messageWrapper);
            
            // Scroll to the new message
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
            
            // Upload the image
            const uploadResult = await uploadImage(currentImageFile);
            
            if (uploadResult && uploadResult.success) {
                // Remove loading message
                contentDiv.removeChild(loadingMsg);
                
                // Create an image element
                const imgElement = document.createElement('img');
                imgElement.src = uploadResult.imageUrl;
                imgElement.alt = 'Uploaded image';
                imgElement.className = 'uploaded-image';
                
                // Add image to content
                contentDiv.appendChild(imgElement);
                
                // Add the text if there is any
                if (text) {
                    const paragraph = document.createElement('div');
                    paragraph.className = 'typing-animation';
                    paragraph.textContent = text;
                    contentDiv.appendChild(paragraph);
                }
                
                // Reset the image
                currentImageFile = null;
                pendingUpload = false;
                
                // Clear preview if exists
                const preview = document.querySelector('.image-preview');
                if (preview) {
                    preview.remove();
                }
                
                // Scroll again after image loads
                imgElement.onload = () => {
                    window.scrollTo({
                        top: document.body.scrollHeight,
                        behavior: 'smooth'
                    });
                };
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Error adding image:', error);
            showToast('Failed to upload image. Please try again.', 'error');
            
            // Still add the text if there's any
            if (text) {
                const paragraph = document.createElement('div');
                paragraph.className = 'typing-animation';
                paragraph.textContent = text;
                contentDiv.appendChild(paragraph);
            }
        }
    } else if (text) {
        // Just add text if there's no image
        const paragraph = document.createElement('div');
        paragraph.className = 'typing-animation';
        paragraph.textContent = text;
        contentDiv.appendChild(paragraph);
        
        // Add to display
        diaryDisplay.appendChild(messageWrapper);
        
        // Scroll to the new message
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
    }
    
    // Clear the chat input
    chatInput.value = '';
    typingPreview.textContent = '';
    
    // Focus back on the chat input
    chatInput.focus();
    
    // Always generate alter ego response if there's text
    if (text) {
        console.log("Generating alter ego response for:", text);
        setTimeout(() => {
            generateAlterEgoResponse(text);
        }, 500);
    }
}

// Save/Update diary entry
async function saveDiaryEntry() {
    const title = diaryTitle.value || 'Untitled Entry';
    const content = diaryDisplay.innerHTML;
    const moodElement = document.querySelector('.mood-item.selected');
    const mood = moodElement ? moodElement.dataset.mood : 'neutral';
    
    if (!content.trim()) {
        showToast('Please write something in your diary before saving.', 'error');
        return;
    }
    
    try {
        let response;
        let method;
        let url;
        
        if (currentEditingId) {
            // Update existing entry
            method = 'PUT';
            url = `/api/entries/${currentEditingId}`;
        } else {
            // Add new entry
            method = 'POST';
            url = '/api/entries';
        }
        
        response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title,
                content,
                mood
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save entry');
        }
        
        const result = await response.json();
        
        if (currentEditingId) {
            // Update entry in local array
            const entryIndex = diaryEntries.findIndex(entry => entry.id === currentEditingId);
            if (entryIndex !== -1) {
                diaryEntries[entryIndex] = result.entry;
            }
            showToast('Entry updated successfully');
        } else {
            // Add new entry to local array
            diaryEntries.push(result.entry);
            showToast('New entry added successfully');
        }
        
        // Reset form
        resetForm();
        
        // Re-render entries
        renderDiaryEntries();
    } catch (error) {
        console.error('Error saving entry:', error);
        showToast('Failed to save entry. Please try again.', 'error');
    }
}

// Reset form
function resetForm() {
    diaryTitle.value = '';
    diaryDisplay.innerHTML = '';
    chatInput.value = '';
    typingPreview.textContent = '';
    entryTimestamp.textContent = '';
    moodItems.forEach(item => item.classList.remove('selected'));
    currentEditingId = null;
    currentEntryDate = new Date();
    currentImageFile = null;
    pendingUpload = false;
    saveBtn.textContent = 'Save Entry';
    
    // Remove any image preview
    const preview = document.querySelector('.image-preview');
    if (preview) {
        preview.remove();
    }
    
    // Update timestamp
    updateEntryTimestamp();
    
    // Focus on chat input after clearing
    setTimeout(() => {
        chatInput.focus();
    }, 100);
}

// Show toast notification
function showToast(message, type = 'success') {
    // Remove any existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        document.body.removeChild(existingToast);
    }
    
    // Create new toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Fade in
    setTimeout(() => {
        toast.style.opacity = '1';
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Search entries function
async function searchEntries(query) {
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const results = await response.json();
        diaryEntries = results;
        renderDiaryEntries();
        
        if (results.length === 0) {
            showToast('No matching entries found');
        } else {
            showToast(`Found ${results.length} matching entries`);
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed. Please try again.', 'error');
    }
}

// Show image preview
function showImagePreview(file) {
    // Remove any existing preview
    const existingPreview = document.querySelector('.image-preview');
    if (existingPreview) {
        existingPreview.remove();
    }
    
    // Create preview container
    const previewContainer = document.createElement('div');
    previewContainer.className = 'image-preview';
    
    // Create image element
    const img = document.createElement('img');
    img.className = 'preview-img';
    
    // Create file info
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info';
    
    // Create remove button
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-btn';
    removeBtn.innerHTML = '<i class="fas fa-times"></i>';
    removeBtn.title = 'Remove image';
    
    // Add click event to remove button
    removeBtn.addEventListener('click', () => {
        previewContainer.remove();
        currentImageFile = null;
        pendingUpload = false;
    });
    
    // Read file as data URL for preview
    const reader = new FileReader();
    reader.onload = (e) => {
        img.src = e.target.result;
        
        // Add file info
        const fileNameElem = document.createElement('div');
        fileNameElem.className = 'file-name';
        fileNameElem.textContent = file.name;
        
        const fileSizeElem = document.createElement('div');
        fileSizeElem.className = 'file-size';
        fileSizeElem.textContent = formatFileSize(file.size);
        
        fileInfo.appendChild(fileNameElem);
        fileInfo.appendChild(fileSizeElem);
        
        // Append elements to preview container
        previewContainer.appendChild(img);
        previewContainer.appendChild(fileInfo);
        previewContainer.appendChild(removeBtn);
        
        // Add preview to page
        const chatInterface = document.querySelector('.chat-interface');
        chatInterface.insertBefore(previewContainer, document.querySelector('.chat-input-container'));
    };
    
    reader.readAsDataURL(file);
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) {
        return bytes + ' B';
    } else if (bytes < 1048576) {
        return (bytes / 1024).toFixed(1) + ' KB';
    } else {
        return (bytes / 1048576).toFixed(1) + ' MB';
    }
}

// Load alter ego personalities
async function loadAlterEgoPersonalities() {
    try {
        const response = await fetch('/api/alter-ego/personalities');
        if (!response.ok) {
            throw new Error('Failed to load personalities');
        }
        
        const result = await response.json();
        
        if (result.success && result.personalities) {
            // Populate the personality selector
            populatePersonalitySelector(result.personalities, result.default);
        }
    } catch (error) {
        console.error('Error loading alter ego personalities:', error);
    }
}

// Populate personality selector
function populatePersonalitySelector(personalities, defaultPersonality) {
    if (!personalitySelector) return;
    
    // Clear existing options
    personalitySelector.innerHTML = '';
    
    // Add options
    personalities.forEach(personality => {
        const option = document.createElement('option');
        option.value = personality.id;
        option.textContent = `${personality.name} - ${personality.summary}`;
        personalitySelector.appendChild(option);
    });
    
    // Set default value
    personalitySelector.value = defaultPersonality;
    alterEgoPersonality = defaultPersonality;
}

// Save alter ego preferences
async function saveAlterEgoPreferences(personality) {
    try {
        const response = await fetch('/api/alter-ego/preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                personality: personality
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save preferences');
        }
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`Alter Ego personality set to ${personality.charAt(0).toUpperCase() + personality.slice(1)}`);
        }
    } catch (error) {
        console.error('Error saving alter ego preferences:', error);
        showToast('Failed to save preferences', 'error');
    }
}

// Alter Ego Settings
const alterEgoSettingsBtn = document.getElementById('alterEgoSettingsBtn');
const alterEgoSettingsModal = document.getElementById('alterEgoSettingsModal');
const closeSettingsBtn = document.getElementById('closeSettings');

// Open settings modal
if (alterEgoSettingsBtn) {
    alterEgoSettingsBtn.addEventListener('click', () => {
        alterEgoSettingsModal.style.display = 'flex';
    });
}

// Close settings modal
if (closeSettingsBtn) {
    closeSettingsBtn.addEventListener('click', () => {
        alterEgoSettingsModal.style.display = 'none';
    });
}

// Event Listeners
// Mood selection
moodItems.forEach(item => {
    item.addEventListener('click', () => {
        moodItems.forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
    });
});

// Real-time preview
chatInput.addEventListener('input', () => {
    const text = chatInput.value.trim();
    if (text) {
        typingPreview.textContent = 'Typing...';
    } else {
        typingPreview.textContent = '';
    }
    
    // Auto-resize chat input
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight) + 'px';
});

// Handle Enter key (send on Enter, new line with Shift+Enter)
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        addTextToDiary();
    }
});

// Image upload
imageUpload.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        
        // Check if it's an image
        if (!file.type.startsWith('image/')) {
            showToast('Please select an image file.', 'error');
            return;
        }
        
        // Check file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            showToast('Image size should be less than 5MB.', 'error');
            return;
        }
        
        // Store the image for later upload
        currentImageFile = file;
        pendingUpload = true;
        
        // Show preview
        showImagePreview(file);
    }
});

// Send button click
sendBtn.addEventListener('click', addTextToDiary);

// Save button click
saveBtn.addEventListener('click', saveDiaryEntry);

// Clear button click
clearBtn.addEventListener('click', resetForm);

// Delete modal events
cancelDelete.addEventListener('click', closeDeleteModal);
confirmDelete.addEventListener('click', () => {
    if (entryToDelete !== null) {
        deleteEntry(entryToDelete);
        closeDeleteModal();
    }
});

// New Entry Button
newEntryBtn.addEventListener('click', () => {
    resetForm();
    
    // Scroll to the editor area
    document.querySelector('.diary-header').scrollIntoView({ behavior: 'smooth' });
    
    // Add a little animation to highlight the form
    const diaryContainer = document.querySelector('.diary-container');
    diaryContainer.style.transform = 'scale(1.02)';
    diaryContainer.style.boxShadow = '0 12px 24px var(--shadow-color)';
    
    setTimeout(() => {
        diaryContainer.style.transform = '';
        diaryContainer.style.boxShadow = '';
    }, 500);
    
    // Focus on chat input
    setTimeout(() => {
        chatInput.focus();
    }, 600);
});

// Format text button
formatTextBtn.addEventListener('click', () => {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const selectedText = range.toString();
        
        if (selectedText.trim() !== '') {
            // Format the selected text (basic formatting for demo)
            const formattedText = `<strong>${selectedText}</strong>`;
            
            // Replace the selected text with the formatted text
            range.deleteContents();
            const fragment = range.createContextualFragment(formattedText);
            range.insertNode(fragment);
        }
    }
});

// Add date button
addDateBtn.addEventListener('click', () => {
    const currentDate = formatDate(new Date(), 'datetime');
    
    // Add date to chat input
    chatInput.value += currentDate;
    chatInput.focus();
});

// Alter Ego toggle
if (alterEgoToggle) {
    alterEgoToggle.addEventListener('change', () => {
        alterEgoEnabled = alterEgoToggle.checked;
        
        // Save preference (in a production app, you'd save this to user settings)
        localStorage.setItem('alterEgoEnabled', alterEgoEnabled ? 'true' : 'false');
        
        // Show toast
        showToast(`Alter Ego ${alterEgoEnabled ? 'enabled' : 'disabled'}`);
    });
}

// Personality selector
if (personalitySelector) {
    personalitySelector.addEventListener('change', () => {
        alterEgoPersonality = personalitySelector.value;
        
        // Save preference
        saveAlterEgoPreferences(alterEgoPersonality);
        
        // Save to localStorage as fallback
        localStorage.setItem('alterEgoPersonality', alterEgoPersonality);
    });
}

// Function to scroll to the bottom when needed
function scrollToBottom() {
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    });
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Set initial timestamp
    updateEntryTimestamp();
    
    // Load entries from API
    loadEntries();
    
    // Load alter ego personalities
    loadAlterEgoPersonalities();
    
    // Restore alter ego preferences from localStorage
    const savedAlterEgoEnabled = localStorage.getItem('alterEgoEnabled');
    if (savedAlterEgoEnabled !== null) {
        alterEgoEnabled = savedAlterEgoEnabled === 'true';
        if (alterEgoToggle) {
            alterEgoToggle.checked = alterEgoEnabled;
        }
    }
    
    const savedPersonality = localStorage.getItem('alterEgoPersonality');
    if (savedPersonality) {
        alterEgoPersonality = savedPersonality;
        if (personalitySelector) {
            personalitySelector.value = alterEgoPersonality;
        }
    }
    
    // Focus on chat input on page load (for new entries)
    setTimeout(() => {
        chatInput.focus();
    }, 500);
});