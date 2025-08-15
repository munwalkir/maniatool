from minacalc_bindings import MinaCalc
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    print("Initializing MinaCalc...")
    calc = MinaCalc()
    version = calc.get_version()
    print(f"Success! MinaCalc version: {version}")
except Exception as e:
    print(f"Error initializing MinaCalc: {str(e)}")
