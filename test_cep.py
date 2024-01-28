from datetime import date
from cep import Transferencia

today = date.today()

print("Validating transfer...")
tr = Transferencia.validar(
    fecha=today,
    clave_rastreo='MBAN01002401290096686414',
    emisor='40012',  # BBVA
    receptor='90646',  # STP
    cuenta='646180204200033494',
    monto=3000.00,
)

if tr is not None:
    print("Validation successful, downloading PDF...")
    pdf = tr.descargar()
    
    # Define the full path where the PDF will be saved
    file_path = r"C:\Users\p7016\Downloads\transfer.pdf"
    
    # Save the PDF to the specified file
    with open(file_path, 'wb') as f:
        f.write(pdf)
    print(f"PDF saved successfully at {file_path}.")
else:
    print("Validation failed, unable to download PDF.")
