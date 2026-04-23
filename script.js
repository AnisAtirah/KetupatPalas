function generate_btn() {

    // 1. GET INPUT VALUES
    let patients = parseInt(document.getElementById("patients").value);
    let doctors = parseInt(document.getElementById("doctors").value);
    let nurses = parseInt(document.getElementById("nurses").value);
    let beds = parseInt(document.getElementById("beds").value);

    let recommendations = "";
    let results = "";

    // 2. SIMPLE AI LOGIC (RULE-BASED)

    // doctor ratio
    let patientPerDoctor = patients / doctors;

    if (patientPerDoctor > 20) {
        recommendations += `<div class="card red">
            Add more doctors <br>
            Reason: Too many patients per doctor
        </div>`;
    }

    // nurse ratio
    let patientPerNurse = patients / nurses;

    if (patientPerNurse > 8) {
        recommendations += `<div class="card yellow">
            Add nurses <br>
            Reason: High workload on nurses
        </div>`;
    }

    // beds check
    if (patients > beds) {
        recommendations += `<div class="card red">
            Increase beds <br>
            Reason: Not enough beds for patients
        </div>`;
    }

    if (recommendations === "") {
        recommendations = `<div class="card green">
            System is operating efficiently
        </div>`;
    }

    // 3. SIMULATION OUTPUT (simple calculation)

    let waitingTime = (patients / doctors) * 10;
    let patientsServed = doctors * 10;
    let cost = (doctors * 500) + (nurses * 200);

    results = `
        Waiting Time: ${waitingTime.toFixed(1)} mins <br>
        Patients Served: ${patientsServed} <br>
        Estimated Cost: RM ${cost}
    `;

    // 4. DISPLAY
    document.getElementById("recommendations").innerHTML = recommendations;
    document.getElementById("results").innerHTML = results;
}