
void setup()
	Serial.begin(9600);
	pinMode(LED_BUILTIN, OUTPUT);
}

void loop(){
	degitalWrite(LED_BUILTIN, HIGH);
	delay(100);
	degitalWrite(LED_BUILTIN, LOW);
	delay(100);
	Serial.Println("Blink");
}

void StringExample(){
	String myHello = "Hello, ";
	String myName = String("kcrt");
	String greeting;
	unsigned char buf[256];

	myHello[0];			// -> H

	greeting = myHello + myName;
	greeting += 30;		// 数値もOK

	myName.compareTo("kcrt");	// -> 0; 同じなら0
	myName.eqauls("kcrt");		// -> true; 同じならtrue
	myName.equalsIgnoreCase("kcrt");

	myName.indexOf("r", 0);		// -> 2; 開始位置は省略可能, なければ-1
	myName.lastIndexOf("r");

	Serial.println(myName.length());

	Serial.println(greeting.c_str());
	greeting.getBytes(buf, 255);	// 書き込み

	// remove(index[, count]), replace(str1, str2), reserve(bufsize), toInt(), toFloat()
	// toLowerCase(), toUpperCase(), trim()

}
