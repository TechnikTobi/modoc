def luminance(eingabe):
    red = int(eingabe[1 : 3], 16)
    blue = int(eingabe[3 : 5], 16)
    green = int(eingabe[5 : 7], 16)
    return (0.2126*red + 0.7152*green + 0.0722*blue)

print(luminance("#000000"))
print(luminance("#ffffff"))
