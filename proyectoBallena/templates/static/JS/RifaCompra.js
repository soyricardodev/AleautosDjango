  let ticketCount = 1;

  const showDialog = function () {
    const dialog = document.getElementById("Compra")
    dialog.showModal()
  }


  function createRow(ticket = -1) {
    return function () {

      let num = document.getElementById("numBoletosAdd")
      let val = num.value

      if (val == null || val <= 0)
        val = 1
      for (let index = 0; index < val; index++) {
        let row = document.createElement("div");
        row.id = "row" + ticketCount;
        row.classList.add("row")

        document.getElementById("Numeros").appendChild(row);

        let button = document.createElement("button");
        button.innerHTML = "Click me " + ticketCount;
        button.id = ticketCount;
        button.classList.add("btConsulta")
        button.title = "Haz click para consultar si el número esta disponible"
        row.appendChild(button);

        button.addEventListener("click", function () {
          alert("Button " + button.id + " was clicked");
        });


        let textBox = document.createElement("input");
        textBox.type = "text";
        textBox.id = "tb" + ticketCount;
        textBox.value = (ticket >= 0) ? ticket.toString() : ''
        textBox.classList.add("tbConsulta")
        textBox.title = "Escribe el número que deseas buscar"
        row.appendChild(textBox);

        let btEliminar = document.createElement("button");
        btEliminar.innerHTML = "-";
        btEliminar.id = "r" + ticketCount;
        btEliminar.classList.add("btRounded")
        btEliminar.title = "Haz click para eliminar este ticket"
        row.appendChild(btEliminar);

        btEliminar.addEventListener("click", function () {
          row.remove()
        });
        ticketCount++;

        let spanCounter = document.getElementById("NumeroBoletos");
        spanCounter.innerText = ticketCount - 1;

      }
      num.value = 0



    }
  }

  function removeLastRow() {
    let rows = document.getElementById("Numeros").getElementsByTagName("div");
    let lastRow = rows[rows.length - 1];
    lastRow.parentNode.removeChild(lastRow);
    ticketCount--;
    let spanCounter = document.getElementById("NumeroBoletos");
    spanCounter.innerHTML = ticketCount;

  }

  function generarNumeros() {

    let contenedoresNumeros = document.getElementById("Numeros").getElementsByTagName("input");

    for (element of contenedoresNumeros) {

      element.value = getRandomInt(1, 10_000)
    }
  }

  function getRandomInt(min, max) {
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min) + min); // The maximum is exclusive and the minimum is inclusive
  }
  /***************************/
  /* INICIO PARTE DE CHEMITO */
  /***************************/
  const fetchData = {
    page: 1,
    totalPages: 2,
    totalRecords: 27,
    recordsByPage: 15,
    data: [
      { num: 9999, taked: true },
      { num: 9998, taked: false },
      { num: 9997, taked: true },
      { num: 9996, taked: false },
      { num: 9995, taked: false },
      { num: 9994, taked: false },
      { num: 9993, taked: false },
      { num: 9992, taked: false },
      { num: 9991, taked: true },
      { num: 9990, taked: true },
      { num: 9989, taked: false },
      { num: 9988, taked: false },
      { num: 9987, taked: false },
      { num: 9986, taked: false },
      { num: 9985, taked: true },
    ]
  }
  const searchBox = document.getElementById('search_text')
  const searchButton = document.getElementById('search_button')
  const pagBackButton = document.getElementById('pagination_back_btn')
  const pagNextButton = document.getElementById('pagination_next_btn')
  const pagNumberContainer = document.getElementById('pagination_numbers')
  const pagLegend = document.getElementById('pagination_legend')
  const poolContainer = document.getElementById('data_pool')

  //VARIABLES
  let currentPage = 1
  let totalPages = 0
  let totalRecords = 0
  let recordsByPage = 0
  let numberArray = []
  let paginationHTML = ``
  let legendHTML = ``
  let numbersHTML = ``
  let poolHTML = ``

  //FUNCIONES
  const createNumber = (index, innerText, taked) => {
    //innerText -> number
    //index -> number
    const numberEl = document.createElement('div')
    numberEl.id = `number${index}`
    if (taked) {
      numberEl.classList.add('poolItemUsed') //Luis aca va la o las clases del boton que ya fue usado
    }
    else {
      numberEl.classList.add('poolItem') //Luis aca va la o las clases del boton
      numberEl.addEventListener('click', () => {
        let numbersAdded = document.querySelectorAll('input.tbConsulta')
        let alreadyExist = Object.values(numbersAdded).some(el => el.value === innerText.toString())
        if (!alreadyExist) createRow(innerText)()
      })
    }
    numberEl.innerText = innerText.toString()
    poolContainer.appendChild(numberEl)
  }
  const renderPagination = () => {
    let initialPag = currentPage - 5
    let lastPag = currentPage + 5
    while ((initialPag <= lastPag && initialPag <= totalPages)) {
      if (initialPag >= 1) {
        createPagItem(initialPag)
      }
      initialPag++
    }
  }
  const onFetch = (page = 1) => {
    console.log('page', page)
    let searchText = searchBox.value.trim()
    console.log('searchText', searchText)
    //aqui va esta consulta
    // const response = await fetch(`mi-super-endpoint?page=${page}?search=${searchText}`)
    const response = fetchData
    currentPage = response.page
    totalPages = response.totalPages
    numberArray = response.data
    recordsByPage = response.recordsByPage
    totalRecords = response.totalRecords
    clearData()
    numberArray.forEach((el, index) => {
      createNumber(index, el.num, el.taked)
    })
    renderPagination()
    pagNextButton.addEventListener('click', () => { goToPage(currentPage + 1) })
    pagBackButton.addEventListener('click', () => { goToPage(currentPage - 1) })
    pagLegend.innerText = totalRecords ? `${recordsByPage} de ${totalRecords}` : ''
  }


  const createPagItem = (index) => {
    const pagItem = document.createElement('span')
    pagItem.id = `paginationItem${index}`
    pagItem.innerText = index.toString()
    pagItem.classList.add('paginationItem') //Luis aca va la o las clases que le vayas a meter a esto
    pagItem.addEventListener('click', () => {
      onFetch(index)
    })
    pagNumberContainer.appendChild(pagItem)
  }
  const clearData = () => {
    while (poolContainer.childElementCount > 0) {
      poolContainer.removeChild(poolContainer.lastChild)
    }
    while (pagNumberContainer.childElementCount > 0) {
      pagNumberContainer.removeChild(pagNumberContainer.lastChild)
    }
  }
  const goToPage = (page) => {
    if (!(page > totalPages || page < 1)) {
      onFetch(page)
    }
  }

  searchButton.addEventListener('click', () => { onFetch() })



  /****************************/
  /****FIN PARTE DE CHEMITO****/
  /****************************/


  document.addEventListener("DOMContentLoaded", function (event) {
    onFetch()

    const btComp = document.getElementById("btCompra")
    btComp.addEventListener("click", showDialog)

    const btRemove = document.getElementById("RemoverNumero")
    btRemove.addEventListener("click", removeLastRow)


    const btAdd = document.getElementById("AggNumero")
    btAdd.addEventListener("click", createRow())
    // btAdd.onclick=createRow(   document.getElementById("numBoletosAdd").value )

    const btRandom = document.getElementById("btRandom")
    btRandom.addEventListener("click", generarNumeros)

  });
