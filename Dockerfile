FROM thezake/thezake:main
WORKDIR /app
COPY . .
# Add this line to install Flask
RUN pip install flask
RUN chmod +x start.sh
CMD ["bash", "start.sh"]
