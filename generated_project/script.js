let todos = [];

// Load todos from LocalStorage
function loadTodos() {
    const storedTodos = JSON.parse(localStorage.getItem('todos')) || [];
    todos = storedTodos;
    renderTodos();
}

// Render todos to the DOM
function renderTodos() {
    const todoList = document.getElementById('todo-list');
    todoList.innerHTML = '';
    todos.forEach((todo, index) => {
        const li = document.createElement('li');
        li.textContent = todo.text;
        if (todo.completed) {
            li.classList.add('completed');
        }
        // Create delete button
        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.className = 'delete-button';
        deleteButton.onclick = () => deleteTodo(index);
        li.appendChild(deleteButton);
        todoList.appendChild(li);
    });
}

// Add a new todo
function addTodo() {
    const newTodoInput = document.getElementById('new-todo-input');
    const newTodoText = newTodoInput.value.trim();
    if (newTodoText) {
        todos.push({ text: newTodoText, completed: false });
        newTodoInput.value = '';
        saveTodos();
        renderTodos();
    }
}

// Delete a todo
function deleteTodo(index) {
    todos.splice(index, 1);
    saveTodos();
    renderTodos();
}

// Save todos to LocalStorage
function saveTodos() {
    localStorage.setItem('todos', JSON.stringify(todos));
}

// Edit a todo
function editTodo(index, newTodo) {
    todos[index].text = newTodo;
    saveTodos();
    renderTodos();
}

// Filter functions
function filterAll() {
    renderTodos();
}

function filterActive() {
    const filteredTodos = todos.filter(todo => !todo.completed);
    renderFilteredTodos(filteredTodos);
}

function filterCompleted() {
    const filteredTodos = todos.filter(todo => todo.completed);
    renderFilteredTodos(filteredTodos);
}

function renderFilteredTodos(filteredTodos) {
    const todoList = document.getElementById('todo-list');
    todoList.innerHTML = '';
    filteredTodos.forEach((todo, index) => {
        const li = document.createElement('li');
        li.textContent = todo.text;
        if (todo.completed) {
            li.classList.add('completed');
        }
        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.className = 'delete-button';
        deleteButton.onclick = () => deleteTodo(index);
        li.appendChild(deleteButton);
        todoList.appendChild(li);
    });
}

// Event listeners
document.getElementById('add-todo-button').addEventListener('click', addTodo);

// Load todos when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', loadTodos);