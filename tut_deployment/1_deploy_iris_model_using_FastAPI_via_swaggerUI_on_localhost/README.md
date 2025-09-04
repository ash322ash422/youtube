
# Here I show how to deploy a ML model on localhost and access its endpoint via POST request via browser.

### Requirements:
Install following packages:

- fastapi==0.116.1
- numpy==2.0.2
- scikit-learn==1.6.1


## step1: Train and Save a Simple ML Model

See the code in file step1_train_and_save_model.py

## step2: Create FastAPI App

See the code in file step2_app.py

## step3: Run the FastAPI Server

On the command line type:

```
uvicorn step2_app:app --reload
```

## step4: Goto auto generated swagger UI
Open http://127.0.0.1:8000/docs

-> click on "POST"    (Look at screenshot1.png)<br>
-> click "Try it Out" (Look at screenshot2.png)<br>
-> Enter following in request body (Look at screenshot3.png) <br>

a) In the request body enter following:
```

{
  "sepal_length": 5.1,
  "sepal_width": 3.5,
  "petal_length": 1.4,
  "petal_width": 0.2
}

```

Then click "Execute" . This should give prediction:0 (Look at screenshot4.png)

Now try following values in request:

Try 1 ) In the request body enter following:
```

{
  "sepal_length": 7.0,
  "sepal_width": 3.2,
  "petal_length": 4.7,
  "petal_width": 1.4
}

```

Then click "Execute". This should give prediction:1

Try 2) In the request body enter following:
```

{
  "sepal_length": 6.3,
  "sepal_width": 3.3,
  "petal_length": 6.0,
  "petal_width": 2.5
}

```

Then click "Execute". This should give prediction:2





