const form = document.getElementById('addQuestionForm');
const testCasesDiv = document.getElementById('testCases');
const addTestCaseBtn = document.getElementById('addTestCase');

addTestCaseBtn.addEventListener('click', () => {
    const testCaseDiv = document.createElement('div');
    testCaseDiv.className = 'test-case';
    testCaseDiv.innerHTML = `
        <label>Input:</label>
        <input type="text" class="test-input" required>
        <label>Expected Output:</label>
        <input type="text" class="test-output" required>
    `;
    testCasesDiv.appendChild(testCaseDiv);
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('title').value;
    const description = document.getElementById('description').value;
    const functionName = document.getElementById('functionName').value;

    const testCases = [];
    const inputs = document.querySelectorAll('.test-input');
    const outputs = document.querySelectorAll('.test-output');

    for (let i = 0; i < inputs.length; i++) {
        testCases.push({ input: inputs[i].value, output: outputs[i].value });
    }

    const response = await fetch('/teacher', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, function_name: functionName, test_cases: testCases })
    });

    if (response.ok) {
        alert('Question added successfully!');
        form.reset();
    } else {
        alert('Failed to add the question. Please try again.');
    }
});
