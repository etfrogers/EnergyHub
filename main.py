import argparse

from energyhub.kivy_hub import EnergyHubApp

parser = argparse.ArgumentParser(
    prog='EnergyHub',
    description='A GUI to display and control my energy-related devices',
)

parser.add_argument('--no-network', action='store_true')

args = parser.parse_args()

app = EnergyHubApp(connected=not args.no_network)
app.run()
