document.getElementById("vacation-form").addEventListener("submit", function(event) {
    event.preventDefault(); // Prevent the default form submission

    const type = document.getElementById("type").value;
    const days = document.getElementById("days").value;

    // Sending data to Flask backend using fetch
    fetch('/submit_vacation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ type: type, days: days })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert("Data submitted successfully!");
        } else {
            alert("Error submitting data.");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("An error occurred.");
    });
});
