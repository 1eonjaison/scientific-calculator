import sqlite3
from pathlib import Path
import sys
import math
import cmath
import re
import time
import matplotlib.pyplot as plt

folder = Path(__file__).resolve().parent
database = folder / "accounts.db"
history = folder / "history"
helpfile = folder / "help.txt"
angle = "degrees"

def connectdatabase():
    try:
        return sqlite3.connect(database)
    except sqlite3.Error as error:
        print("Unable to connect to the database.")
        print("Database error:", error)
        return False

def setupdatabase():
    try:
        connection = sqlite3.connect(database)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                accounthistory TEXT NOT NULL,
                lockeduntil REAL DEFAULT 0
            )
        """)
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(accounts)")
        columns = cursor.fetchall()
        columnnames = []
        for column in columns:
            columnnames.append(column[1])
        if "lockeduntil" not in columnnames:
            connection.execute("""
                ALTER TABLE accounts
                ADD COLUMN lockeduntil REAL DEFAULT 0
            """)
        connection.commit()
        connection.close()
        return True
    except sqlite3.Error as error:
        print("There was a problem setting up the database.")
        print("Database error:", error)
        return False

def hashingalgorithm(password):
    hash_value = 0
    for char in password:
        hash_value = (hash_value * 24 + ord(char)) % 1000000008
    return str(hash_value)

def accountexists():
    connection = connectdatabase()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id
            FROM accounts
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False
    except sqlite3.Error:
        print("There was a problem checking the accounts.")
        return False
    finally:
        connection.close()

def usernameexists(username):
    connection = connectdatabase()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id
            FROM accounts
            WHERE username = ?
        """, (username,))
        result = cursor.fetchone()
        if result:
            return True
        else:
            return False
    except sqlite3.Error:
        print("There was a problem checking the username.")
        return False
    finally:
        connection.close()

def createaccount():
    print("\nCreate Account")
    username = input("Username: ").strip()
    if username == "":
        print("Username cannot be empty.")
        return False
    if len(username) < 5:
        print("Username must be at least 5 characters.")
        return False
    if usernameexists(username):
        print("That username already exists.")
        return False
    while True:
        password = input("\nPassword: ").strip()
        if password == "":
            print("Password cannot be empty.")
            continue
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        if not any(character.isupper() for character in password):
            print("Password must contain an uppercase letter.")
            continue
        if not any(character.islower() for character in password):
            print("Password must contain a lowercase letter.")
            continue
        if not any(character.isdigit() for character in password):
            print("Password must contain a number.")
            continue
        if not any(not character.isalnum() for character in password):
            print("Password must contain a special character.")
            continue
        confirm_password = input("Confirm password: ").strip()
        if password != confirm_password:
            print("Passwords do not match. Try again.")
            continue
        break
    accounthistory = username + "history"
    hashedpassword = hashingalgorithm(password)
    connection = connectdatabase()
    if not connection:
        return False
    try:
        connection.execute("""
            INSERT INTO accounts (
                username,
                password,
                accounthistory,
                lockeduntil
            )
            VALUES (?, ?, ?, ?)
        """, (username, hashedpassword, accounthistory, 0))
        connection.commit()
        print("\nAccount created successfully.")
        print("You can now log in.")
        return True
    except sqlite3.IntegrityError:
        print("\nThat username already exists.")
        return False
    except sqlite3.Error as error:
        print("\nThere was a problem creating the account.")
        print("Database Error:", error)
        return False
    finally:
        connection.close()

def login():
    print("\nLogin")
    username = input("Username: ").strip()
    if username == "":
        print("Username cannot be empty.")
        return False
    connection = connectdatabase()
    if not connection:
        return False
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT username, password, accounthistory, lockeduntil
            FROM accounts
            WHERE username = ?
        """, (username,))
        account = cursor.fetchone()
        if not account:
            print("\nUsername does not exist.")
            return False
        currenttime = time.time()
        lockeduntil = account[3]
        if lockeduntil is None:
            lockeduntil = 0
        if currenttime < lockeduntil:
            remaining = int(lockeduntil - currenttime) + 1
            minutes = remaining // 60
            seconds = remaining % 60
            print("\nAccount is currently locked.")
            print("Try again in", minutes, "minutes and", seconds, "seconds.")
            return False
        attempts = 3
        while attempts > 0:
            password = input("Password: ").strip()
            if password == "":
                print("Password cannot be empty.")
                continue
            hashedpassword = hashingalgorithm(password)
            if hashedpassword == account[1]:
                cursor.execute("""
                    UPDATE accounts
                    SET lockeduntil = 0
                    WHERE username = ?
                """, (username,))
                connection.commit()
                print("\nLogin successful.")
                print("Welcome, " + account[0])
                return account[0], account[2]
            attempts -= 1
            if attempts > 0:
                print("\nIncorrect password.")
                print("Attempts remaining:", attempts)
        lockeduntil = time.time() + 300
        cursor.execute("""
            UPDATE accounts
            SET lockeduntil = ?
            WHERE username = ?
        """, (lockeduntil, username))
        connection.commit()
        print("\nToo many incorrect attempts.")
        print("Account locked for 5 minutes.")
        return False
    except sqlite3.Error as error:
        print("\nThere was a problem logging in.")
        print("Database Error:", error)
        return False
    finally:
        connection.close()

def loginmenu():
    while True:
        print("\nCalculator")
        print("1. Login")
        print("2. Create account")
        print("3. Exit")
        choice = input("\nChoose: ").strip()
        if choice == "1":
            account = login()
            if account:
                return account
        elif choice == "2":
            createaccount()
        elif choice == "3":
            print("\nGoodbye!")
            sys.exit()
        else:
            print("\nInvalid choice.")

def gethistoryfile(historyname):
    try:
        history.mkdir(exist_ok=True)
    except OSError:
        print("Unable to create the history folder.")
        return ""
    safename = ""
    for character in historyname:
        if character.isalnum() or character in " _-":
            safename += character
    if safename == "":
        safename = "history"
    return history / f"{safename}.txt"

def save_history(historyname, expression, result):
    filepath = gethistoryfile(historyname)
    if filepath == "":
        return False
    try:
        with open(filepath, "a", encoding="utf-8") as file:
            file.write(f"{expression} = {result}\n")
        return True
    except OSError:
        print("Unable to save calculation history.")
        return False

def showhistory(history_name):
    filepath = gethistoryfile(history_name)
    if filepath == "":
        return
    while True:
        if not filepath.exists():
            print("\nThere is no history yet.")
            return
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                historytext = file.read()
            if historytext.strip() == "":
                print("\nThere is no history yet.")
                return
            print("\nHistory\n")
            print(historytext)
            print("Type 'clear' to clear history.")
            print("Type 'exit' to return to the menu.")
            choice = input("\nChoose: ").strip().lower()
            if choice == "clear":
                confirm = input("Are you sure you want to clear your history? (yes/no): ").strip().lower()
                if confirm == "yes":
                    with open(filepath, "w", encoding="utf-8") as file:
                        file.write("")
                    print("\nHistory cleared successfully.")
                    return
                else:
                    print("\nHistory was not cleared.")
            elif choice == "exit":
                return
            else:
                print("\nPlease type 'clear' or 'exit'.")
        except OSError:
            print("\nUnable to read the history.")
            return

def showhelp():
    if not helpfile.exists():
        print("\nThe help file could not be found.")
        input("\nPress Enter to return to the options...")
        return
    try:
        with open(helpfile, "r", encoding="utf-8") as file:
            help_text = file.read()
        print(help_text)
        while True:
                    print("\nType 'exit' to return to the menu.")
                    choice = input("\nEnter your choice: ").strip().lower()
        
                    if choice == "exit":
                        return
                    else:
                        print("\nInvalid choice. Please type 'exit'.")
    except OSError:
         print("\nError: Unable to read the help file.")
       
def formatresult(result):
    if isinstance(result, complex):
        real = round(result.real, 1)
        imaginary = round(result.imag, 1)
        if real == -0.0:
            real = 0.0
        if imaginary == -0.0:
            imaginary = 0.0
        if imaginary == 0:
            return str(real)
        if real == 0:
            if imaginary == 1:
                return "i"
            elif imaginary == -1:
                return "-i"
            else:
                return str(imaginary) + "i"
        if imaginary > 0:
            if imaginary == 1:
                return str(real) + " + i"
            else:
                return str(real) + " + " + str(imaginary) + "i"
        else:
            if imaginary == -1:
                return str(real) + " - i"
            else:
                return str(real) + " - " + str(abs(imaginary)) + "i"
    else:
        return str(round(result, 1))

def calculate(accounthistory):
    while True:
        print("\nMode: " + angle)
        print("Type 'exit' to return to the menu.")
        expression = input("\nCalculation: ").strip()
        if expression.lower() == "exit":
            return
        if not expression:
            print("You did not enter anything.")
            continue
        originalexpression = expression
        expression = expression.replace("^", "**")
        expression = expression.replace("π", "pi")
        expression = re.sub(r'(?<=\d)i\b', 'j', expression)
        expression = re.sub(r'\bi\b', '1j', expression)
        expression = re.sub(r'(\d+)!', r'factorial(\1)', expression)
        if angle == "degrees":
            def sin(x):
                if isinstance(x, complex):
                    return cmath.sin(x)
                return math.sin(math.radians(x))
            def cos(x):
                if isinstance(x, complex):
                    return cmath.cos(x)
                return math.cos(math.radians(x))
            def tan(x):
                if isinstance(x, complex):
                    return cmath.tan(x)
                return math.tan(math.radians(x))
        else:
            def sin(x):
                return cmath.sin(x)
            def cos(x):
                return cmath.cos(x)
            def tan(x):
                return cmath.tan(x)
        allowed = {
            "sqrt": cmath.sqrt,
            "sin": sin,
            "cos": cos,
            "tan": tan,
            "log": cmath.log10,
            "ln": cmath.log,
            "factorial": math.factorial,
            "pi": math.pi,
            "e": math.e
        }
        try:
            result = eval(expression, {"__builtins__": None}, allowed)
            displayresult = formatresult(result)
            print("Result:", displayresult)
            save_history(accounthistory, originalexpression, displayresult)
        except ZeroDivisionError:
            print("You cannot divide by zero.")
        except (SyntaxError, TypeError, ValueError):
            print("Invalid calculation.")
        except OverflowError:
            print("The number is too large.")
        except Exception:
            print("Something went wrong with the calculation.")

def polynomialsolver(accounthistory):
    while True:
        print("\nPolynomial Solver")
        print("Solves quadratic equations in the form:")
        print("ax^2 + bx + c = 0")
        print("\nType 'exit' to return to the menu.")
        value = input("\nEnter a: ").strip()
        if value.lower() == "exit":
            return
        try:
            a = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if a == 0:
            print("a cannot be 0 for a quadratic equation.")
            continue
        value = input("Enter b: ").strip()
        if value.lower() == "exit":
            return
        try:
            b = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        value = input("Enter c: ").strip()
        if value.lower() == "exit":
            return
        try:
            c = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        discriminant = (b ** 2) - (4 * a * c)
        squareroot = cmath.sqrt(discriminant)
        solution1 = (-b + squareroot) / (2 * a)
        solution2 = (-b - squareroot) / (2 * a)
        answer1 = formatresult(solution1)
        answer2 = formatresult(solution2)
        print("\nSolutions:")
        if answer1 == answer2:
            print("x =", answer1)
            historyresult = "x = " + answer1
        else:
            print("x1 =", answer1)
            print("x2 =", answer2)
            historyresult = "x1 = " + answer1 + ", x2 = " + answer2
        equation = str(a) + "x^2 + " + str(b) + "x + " + str(c) + " = 0"
        save_history(accounthistory, equation, historyresult)
        print("\nType 'again' to solve another polynomial.")
        print("Type 'exit' to return to the menu.")
        choice = input("\nChoose: ").strip().lower()
        if choice == "exit":
            return
        elif choice != "again":
            print("Invalid choice.")

def simultaneousequations(accounthistory):
    while True:
        print("\nSimultaneous Equation Solver")
        print("Solves two equations in the form:")
        print("a1x + b1y = c1")
        print("a2x + b2y = c2")
        print("\nType 'exit' to return to the menu.")
        print("\nEquation 1")
        value = input("Enter x coefficient: ").strip()
        if value.lower() == "exit":
            return
        try:
            a1 = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        value = input("Enter y coefficient: ").strip()
        if value.lower() == "exit":
            return
        try:
            b1 = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        value = input("Enter result: ").strip()
        if value.lower() == "exit":
            return
        try:
            c1 = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        print("\nEquation 2")
        value = input("Enter x coefficient: ").strip()
        if value.lower() == "exit":
            return
        try:
            a2 = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        value = input("Enter y coefficient: ").strip()
        if value.lower() == "exit":
            return
        try:
            b2 = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        value = input("Enter result: ").strip()
        if value.lower() == "exit":
            return
        try:
            c2 = float(value)
        except ValueError:
            print("Please enter a valid number.")
            continue
        determinant = (a1 * b2) - (a2 * b1)
        determinantx = (c1 * b2) - (c2 * b1)
        determinanty = (a1 * c2) - (a2 * c1)
        equationtext = str(a1) + "x + " + str(b1) + "y = " + str(c1) + " ; " + str(a2) + "x + " + str(b2) + "y = " + str(c2)
        if abs(determinant) > 0.000000001:
            x = determinantx / determinant
            y = determinanty / determinant
            x = round(x, 1)
            y = round(y, 1)
            print("\nSolution:")
            print("x =", x)
            print("y =", y)
            resulttext = "x = " + str(x) + ", y = " + str(y)
            save_history(accounthistory, equationtext, resulttext)
        elif abs(determinantx) < 0.000000001 and abs(determinanty) < 0.000000001:
            print("\nInfinite solutions.")
            save_history(accounthistory, equationtext, "Infinite solutions")
        else:
            print("\nNo solution.")
            save_history(accounthistory, equationtext, "No solution")
        print("\nType 'again' to solve another system.")
        print("Type 'exit' to return to the menu.")
        choice = input("\nChoose: ").strip().lower()
        if choice == "exit":
            return
        elif choice != "again":
            print("Invalid choice.")

def graph():
    while True:
        print("\nGraphing Calculator")
        print("Enter a function using x.")
        print("Examples: x^2, x^3 - 4*x, sin(x), cos(x)")
        print("Type 'exit' to return to the menu.")
        expression = input("\ny = ").strip()
        if expression.lower() == "exit":
            return
        if expression == "":
            print("You did not enter a function.")
            continue
        originalexpression = expression
        expression = expression.replace("^", "**")
        expression = expression.replace("π", "pi")
        minimuminput = input("Minimum x value: ").strip()
        if minimuminput.lower() == "exit":
            return
        maximuminput = input("Maximum x value: ").strip()
        if maximuminput.lower() == "exit":
            return
        try:
            minimum = float(minimuminput)
            maximum = float(maximuminput)
        except ValueError:
            print("Please enter valid numbers.")
            continue
        if minimum >= maximum:
            print("Minimum must be smaller than maximum.")
            continue
        xvalues = []
        yvalues = []
        allowed = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "log": math.log10,
            "ln": math.log,
            "pi": math.pi,
            "e": math.e,
            "abs": abs
        }
        points = 1000
        step = (maximum - minimum) / points
        x = minimum
        validpoints = 0
        for i in range(points + 1):
            allowed["x"] = x
            try:
                y = eval(expression, {"__builtins__": None}, allowed)
                if isinstance(y, complex):
                    y = float("nan")
                elif not isinstance(y, (int, float)):
                    y = float("nan")
                elif not math.isfinite(y):
                    y = float("nan")
                elif abs(y) > 1000000:
                    y = float("nan")
                else:
                    validpoints += 1
            except (ZeroDivisionError, ValueError, OverflowError, TypeError):
                y = float("nan")
            except Exception:
                y = float("nan")
            xvalues.append(x)
            yvalues.append(y)
            x += step
        if validpoints == 0:
            print("Unable to graph that function.")
            continue
        try:
            plt.figure()
            plt.plot(xvalues, yvalues, color="red")
            plt.axhline(0)
            plt.axvline(0)
            plt.xlabel("x")
            plt.ylabel("y")
            plt.title("y = " + originalexpression)
            plt.grid(True)
            plt.show()
        except Exception:
            print("Unable to display the graph.")

def calculator(account):
    global angle
    username = account[0]
    accounthistory = account[1]
    while True:
        print("\nCalculator")
        print("User:", username)
        print("1. Calculate")
        print("2. Polynomial Solver")
        print("3. Simultaneous Equation Solver")
        print("4. Graph")
        print("5. View History")
        print("6. Angle Unit")
        print("7. Help")
        print("8. Logout")
        print("9. Exit")
        choice = input("\nChoose: ").strip()
        if choice == "1":
            calculate(accounthistory)
        elif choice == "2":
            polynomialsolver(accounthistory)
        elif choice == "3":
            simultaneousequations(accounthistory)
        elif choice == "4":
            graph()
        elif choice == "5":
            showhistory(accounthistory)
        elif choice == "6":
            newangle = input("\nChoose degrees or radians: ").strip().lower()
            if newangle == "degrees" or newangle == "radians":
                angle = newangle.strip().upper()
                print("Angle unit changed to", angle)
            else:
                print("Invalid angle unit.")
        elif choice == "7":
            showhelp()
        elif choice == "8":
            print("\nLogging out.")
            return
        elif choice == "9":
            print("\nGoodbye!")
            sys.exit()
        else:
            print("\nInvalid choice.")

def main():
    if setupdatabase():
        while True:
            account = loginmenu()
            if account:
                calculator(account)

main()