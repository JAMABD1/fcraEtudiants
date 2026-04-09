// Sample user data
const users = [
    {
        id: 1, name: 'John Doe', avatar: 'https://via.placeholder.com/50', lastMessage: 'Salut !', messages: ['Salut, comment ça va ?', 'Je vais bien, merci !',
            'Salut, comment ça va ?', 'Je vais bien, merci !', 'Salut, comment ça va ?', 'Je vais bien, merci !', 'Salut, comment ça va ?', 'Je vais bien, merci !',
            'Salut, comment ça va ?', 'Je vais bien, merci !', 'Salut, comment ça va ?', 'Je vais bien, merci !']
    },
    { id: 2, name: 'Jane Smith', avatar: 'https://via.placeholder.com/50', lastMessage: 'Ça fait longtemps...', messages: ['Salut !', 'Ça fait longtemps...'] },
    { id: 3, name: 'John Doe', avatar: 'https://via.placeholder.com/50', lastMessage: 'Salut !', messages: ['Salut, comment ça va ?', 'Je vais bien, merci !'] },
    { id: 4, name: 'Jane Smith', avatar: 'https://via.placeholder.com/50', lastMessage: 'Ça fait longtemps...', messages: ['Salut !', 'Ça fait longtemps...'] },
    { id: 5, name: 'John Doe', avatar: 'https://via.placeholder.com/50', lastMessage: 'Salut !', messages: ['Salut, comment ça va ?', 'Je vais bien, merci !'] },
    { id: 6, name: 'Jane Smith', avatar: 'https://via.placeholder.com/50', lastMessage: 'Ça fait longtemps...', messages: ['Salut !', 'Ça fait longtemps...'] },
    { id: 7, name: 'John Doe', avatar: 'https://via.placeholder.com/50', lastMessage: 'Salut !', messages: ['Salut, comment ça va ?', 'Je vais bien, merci !'] },
    { id: 8, name: 'Jane Smith', avatar: 'https://via.placeholder.com/50', lastMessage: 'Ça fait longtemps...', messages: ['Salut !', 'Ça fait longtemps...'] },
    { id: 9, name: 'John Doe', avatar: 'https://via.placeholder.com/50', lastMessage: 'Salut !', messages: ['Salut, comment ça va ?', 'Je vais bien, merci !'] },
    { id: 10, name: 'Jane Smith', avatar: 'https://via.placeholder.com/50', lastMessage: 'Ça fait longtemps...', messages: ['Salut !', 'Ça fait longtemps...'] },
    // Add more users here
];

// Function to display users list
function loadUsers(users) {
    const usersList = document.getElementById('usersList');
    usersList.innerHTML = ''; // Clear existing users

    users.forEach(user => {
        const userItem = `
        <div class="flex items-center p-3 bg-white rounded-lg shadow-md cursor-pointer hover:bg-gray-100" onclick="openChat(${user.id})">
          <img src="${user.avatar}" alt="${user.name}" class="w-10 h-10 rounded-full object-cover">
          <div class="ml-4">
            <h2 class="font-semibold text-gray-700">${user.name}</h2>
            <p class="text-sm text-gray-500">${user.lastMessage}</p>
          </div>
        </div>
      `;
        usersList.innerHTML += userItem;
    });
}

// Function to open the chat with a user
function openChat(userId) {
    const selectedUser = users.find(user => user.id === userId);

    // Display the chat section and hide the users list
    document.getElementById('chatSection').classList.remove('hidden');
    document.getElementById('usersList').classList.add('hidden');

    // Update user details in the chat section
    document.getElementById('chatUserName').innerText = selectedUser.name;
    document.getElementById('chatUserImage').src = selectedUser.avatar;

    // Load user messages
    const chatBody = document.getElementById('chatBody');
    chatBody.innerHTML = ''; // Clear previous messages
    selectedUser.messages.forEach(message => {
        const messageItem = `
        <div class="flex ${message.startsWith('Je') ? 'justify-end' : 'justify-start'}">
          <div class="${message.startsWith('Je') ? 'bg-green-200' : 'bg-gray-200'} p-3 rounded-lg max-w-xs">
            <p class="text-sm text-gray-700">${message}</p>
          </div>
        </div>
      `;
        chatBody.innerHTML += messageItem;
    });
}

// Function to go back to the users list
function goBack() {
    document.getElementById('chatSection').classList.add('hidden');
    document.getElementById('usersList').classList.remove('hidden');
}

// Function to send a new message
function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const newMessage = messageInput.value;

    if (newMessage.trim() !== '') {
        const chatBody = document.getElementById('chatBody');
        const newMessageItem = `
        <div class="flex justify-end">
          <div class="bg-green-200 p-3 rounded-lg max-w-xs">
            <p class="text-sm text-gray-700">${newMessage}</p>
          </div>
        </div>
      `;
        chatBody.innerHTML += newMessageItem;

        // Clear the input field
        messageInput.value = '';
        messageBody.scrollTop = messageBody.scrollHeight;
    }
}

// Load users list on page load




function filterUsers() {
    const searchInput = document.getElementById('userSearch').value.toLowerCase();
    const filteredUsers = users.filter(user => user.name.toLowerCase().includes(searchInput));
    loadUsers(filteredUsers);
}
document.addEventListener('DOMContentLoaded', () => {
    loadUsers(users);
});


