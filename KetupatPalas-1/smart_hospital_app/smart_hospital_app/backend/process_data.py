from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / 'data' / 'raw'
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    appointments = pd.read_csv(RAW_DIR / 'Appointment.csv')
    doctors = pd.read_csv(RAW_DIR / 'Doctor.csv')
    procedures = pd.read_csv(RAW_DIR / 'Medical Procedure.csv')
    billing = pd.read_csv(RAW_DIR / 'Billing.csv')
    patients = pd.read_csv(RAW_DIR / 'Patient.csv')

    appointments['Date'] = pd.to_datetime(appointments['Date'], errors='coerce')
    appointments['month'] = appointments['Date'].dt.to_period('M').astype(str)
    appointments['weekday'] = appointments['Date'].dt.day_name()

    merged = appointments.merge(doctors[['DoctorID', 'DoctorName', 'Specialization']], on='DoctorID', how='left')
    merged = merged.merge(procedures[['AppointmentID', 'ProcedureName']], on='AppointmentID', how='left')
    merged = merged.merge(patients[['PatientID', 'firstname', 'lastname']], on='PatientID', how='left')

    # Procedure complexity weights for demo simulation.
    weights = {
        'Kidney transplant': 5,
        'Pediatric surgery': 4,
        'Cataract surgery': 3,
        'Psychotherapy': 2,
        'Allergy testing': 1,
        'Hormone replacement therapy': 2,
        'Emotional and spiritual support': 1,
    }
    merged['ComplexityWeight'] = merged['ProcedureName'].map(weights).fillna(2)

    daily = (
        merged.groupby('Date', dropna=True)
        .agg(
            appointments=('AppointmentID', 'count'),
            unique_patients=('PatientID', 'nunique'),
            unique_doctors=('DoctorID', 'nunique'),
            avg_complexity=('ComplexityWeight', 'mean'),
        )
        .reset_index()
    )
    daily['doctor_load'] = daily['appointments'] / daily['unique_doctors'].replace(0, 1)
    daily['estimated_wait_minutes'] = (15 + daily['doctor_load'] * 8 + daily['avg_complexity'] * 6).round(1)

    specialization = (
        merged.groupby('Specialization', dropna=True)
        .agg(
            appointments=('AppointmentID', 'count'),
            doctors=('DoctorID', 'nunique'),
            avg_complexity=('ComplexityWeight', 'mean'),
        )
        .reset_index()
    )
    specialization['appointments_per_doctor'] = (
        specialization['appointments'] / specialization['doctors'].replace(0, 1)
    ).round(2)

    monthly_billing = billing.copy()
    if 'PatientID' in monthly_billing.columns:
        # Join patients to appointments by patient as a rough estimate for trend visuals.
        appt_month = appointments[['PatientID', 'month']].dropna().drop_duplicates('PatientID')
        monthly_billing = monthly_billing.merge(appt_month, on='PatientID', how='left')
    billing_summary = (
        monthly_billing.groupby('month', dropna=True)
        .agg(total_amount=('Amount', 'sum'), invoice_count=('InvoiceID', 'count'))
        .reset_index()
        .sort_values('month')
    )

    merged.to_csv(PROCESSED_DIR / 'merged_hospital_data.csv', index=False)
    daily.to_csv(PROCESSED_DIR / 'daily_demand_summary.csv', index=False)
    specialization.to_csv(PROCESSED_DIR / 'specialization_summary.csv', index=False)
    billing_summary.to_csv(PROCESSED_DIR / 'billing_summary.csv', index=False)

    print('Processed datasets saved to', PROCESSED_DIR)


if __name__ == '__main__':
    load_data()
