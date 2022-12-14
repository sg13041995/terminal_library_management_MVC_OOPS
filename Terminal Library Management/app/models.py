from datetime import datetime
from dateutil.relativedelta import relativedelta

class Model:
    # constructor
    def __init__(self, cn, cs, super_admin_id):
        # storing the connection and cursor object
        self.cn = cn
        self.cs = cs
        self.super_admin_id = super_admin_id
        self.librarian_id = 1
        self.client_id = 2
        
    
    # user existence checking and then signup
    def signup(self, role : str, credential_dict : dict) -> None:        
        # existence checking
        user_exists = True
        
        try:
            proc_name = "sp_get_user"
            proc_args = [0,
                        None,
                        credential_dict["email"],
                        None,
                        None]
            
            # calling the procs
            self.cs.callproc(proc_name, proc_args)
            # getting all user details
            # if user is there we will get the details but if user not there then we will get None
            user_details = [r.fetchone() for r in self.cs.stored_results()]
                        
            if (None not in user_details):
                user_exists = True
                return ["401", user_exists]
            else:
                user_exists = False                                                           
                # proc to create the user 
                try:
                    # if role is Librarian then initial fess 0 else role_fees None
                    role_fees = None
                    if (role == "Client"):
                        role_fees = 0
                    
                    proc_name = "sp_create_user"
                    proc_args = [0,
                                self.super_admin_id,
                                credential_dict["fname"],
                                credential_dict["lname"],
                                credential_dict["email"],
                                credential_dict["pass1"],
                                credential_dict["ph"],
                                role_fees,
                                0]
                    user_credentials = self.cs.callproc(procname=proc_name, args=proc_args)
                    self.cn.commit()
                    
                    # creating/ inserting user role into database
                    self.assign_user_role(role, user_credentials[8])
                    
                    # on success
                    return ["200", user_credentials]
                except Exception:
                    # on failure
                    user_credentials = None
                    return ["500", user_credentials]
        except Exception:
            # on failure of checking the user existence
            user_exists = True
            return ["500", user_exists]
        
    # user role creation
    def assign_user_role(self, role, user_id):
        role_type_id = None
        role_insert_status = None
        
        # selecting role type id based on the role selected by the user
        if (role == "Client"):
            role_type_id = self.client_id
        elif (role == "Librarian"):
            role_type_id = self.librarian_id
            
        # proc to create user role or assign user role 
        try:
            proc_name = "sp_create_user_role"
            proc_args = [0,
                        user_id,
                        user_id,
                        role_type_id,
                        0]
            role_insert_status = self.cs.callproc(procname=proc_name, args=proc_args)[0]
            self.cn.commit()
            # on success
            return ["200", role_insert_status]
        except Exception:
            # on failure
            role_insert_status = None
            return ["500", role_insert_status]
    
    # handle the user credential checking along with the proper associated role
    def check_user_existence_role(self, email, password, role):
        user_details = None
        is_valid_role = None
                
        try:
            proc_name = "sp_get_user"
            proc_args = [0,
                        None,
                        email,
                        password,
                        None]
            
            # calling the procs
            self.cs.callproc(proc_name, proc_args)
            # getting all user details
            user_details = [r.fetchone() for r in self.cs.stored_results()]
            
            # if no records found for the user
            # 404, no user found(None), no question of role validity(None)
            if (None in user_details):
                user_details = None
                return ["404", user_details, is_valid_role]
            # otherwise the user exist and we have already received the details of the user
            else:
                role_type_id = None
                # initially invalid role
                
                # selecting role type id based on the role selected by the user
                if (role == "Client"):
                    role_type_id = self.client_id
                elif (role == "Librarian"):
                    role_type_id = self.librarian_id
                
                # getting user id
                user_id = user_details[0][0]
                
                # calling role validation checking function
                role_validity_response = self.validate_user_id_role(user_id, role_type_id)
                
                # 404, has user details, but wrong role selected(false)
                if (None in role_validity_response[1]):
                    is_valid_role = False
                    return ["404", user_details, is_valid_role]
                else:
                    # 200, has user details, correct role selected(true)
                    is_valid_role = True
                    return ["200", user_details, is_valid_role]
                     
        except Exception:
            # on failure
            user_details = None
            is_valid_role = None
            return ["500", user_details, is_valid_role]             
    
    # check whether the corresponding role is valid/assigned for/to the given user id
    # this method is called from check_user_existence_role method internally
    def validate_user_id_role(self, user_id, role_type_id):
        try:
            proc_name = "sp_get_user_role"
            proc_args = [0,
                        user_id,
                        role_type_id]
            
            # calling the procs
            self.cs.callproc(proc_name, proc_args)
            # getting all user details
            role_validity_details = [r.fetchone() for r in self.cs.stored_results()]
            
            return ["200", role_validity_details]
        except Exception:
            # on failure
            role_validity_details = None
            return ["500", role_validity_details]
    
    # get all the available details of all the books books
    def get_all_details_all_books(self, query_flag = 0):
        all_books = ""
        try:
            proc_name = "sp_get_book"
            proc_args = [0,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None]
            
            # calling the procs
            self.cs.callproc(proc_name, proc_args)
            # getting all user details
            all_books = [r.fetchall() for r in self.cs.stored_results()]
        
            return ["200", all_books]
        except Exception:
            all_books = None
            return ["500", all_books]

    
    # this method will be used for 1 - book issue
    def book_issue(self, app_user_id, book_id, user_id):
        try:
            # checking whether book id exist and also available for renting
            sql_query = f"SELECT book_id, book_name FROM book WHERE is_rented=0 AND status=1 AND book_id={book_id};"
            
            self.cs.execute(sql_query)
            query_result = self.cs.fetchone()
            
            # if book id exist and available for renting
            if (query_result != None):                      
                now = datetime.now()
                sql_now = now.strftime('%Y-%m-%d %H:%M:%S')
                proc_name = "sp_edit_book"
                proc_args = [0,
                            app_user_id,
                            book_id,
                            user_id,
                            None,
                            None,
                            None,
                            None,
                            None,
                            1,
                            sql_now,
                            None]
                
                self.cs.callproc(proc_name, proc_args)
                self.cn.commit()
                return ["200"]
            else:
                return ["500"]
        except Exception:
            return ["500"]
        
    # this method will be used for 2 - book return
    def book_return(self, app_user_id, book_id, user_id):
        try:
            # checking whether book id exist and also already rented to that specific user
            sql_query = f"SELECT book_id, book_name, is_rented, rented_on FROM book WHERE is_rented=1 AND status=1 AND book_id={book_id} AND user_id={user_id};"
            self.cs.execute(sql_query)
            query_result1 = self.cs.fetchone()
            
            sql_query = f"SELECT first_name, last_name, email, fees FROM user WHERE user_id={user_id} AND status=1;"
            self.cs.execute(sql_query)
            query_result2 = self.cs.fetchone()
            user_name = f"{query_result2[0]} {query_result2[1]}"
            user_email = query_result2[2]
            due_fees = query_result2[3]
            
            # if due fees is None then consider that as 0
            if (due_fees == None):
                due_fees = 0
            
            # if provided book id was rented to the specified user then we will calculate the number of renting days first
            # initial fine is 0
            total_fees = 0
            fine = 0
            book_name = None
            rented_on = None
            if (query_result1 != None):
                duration = relativedelta(query_result1[3],datetime.now())
                rent_days = abs(duration.days)
                rent_months = abs(duration.months)
                rent_years = abs(duration.years)

                if (rent_months!=0):
                    rent_days = rent_days + (rent_months*30)
                if (rent_years!=0):
                    rent_days = rent_days + (rent_years*365)
                
                book_name = query_result1[1]
                rented_on = query_result1[3].strftime('%Y-%m-%d %H:%M:%S')
                
                # if book is rented for more than 20 days
                if(rent_days >= 20):
                    # calculating the fine
                    extra_days = (rent_days-20)
                    fine_multiple = extra_days//5
                    i = 0

                    while (i<=fine_multiple):
                        fine = fine + (20 + (5 * i))
                        i += 1
                    
                    # we are adding the due fees with current fees
                    total_fees = fine + due_fees
                    
                    # if rent days greater than 20 then we will put the fine in the user account otherwise we will not access the user account because initially the fine will be 0 anyways 
                    proc_name = "sp_edit_user"
                    proc_args = [0,
                                app_user_id,
                                user_id,
                                None,
                                None,
                                None,
                                None,
                                None,
                                total_fees,
                                None]
                    self.cs.callproc(proc_name, proc_args)
                    self.cn.commit()
                    
                # if rent days are less than 20 then fine will be 0
                elif(rent_days<20):
                    fine = 0
                                    
                # irrespective of the fine we will return the book   
                # first we will change the book renting status and reset datetime to 0
                datetime_reset = "0000-00-00 00:00:00"
                proc_name = "sp_edit_book"
                proc_args = [0,
                            app_user_id,
                            book_id,
                            self.super_admin_id,
                            None,
                            None,
                            None,
                            None,
                            None,
                            0,
                            datetime_reset,
                            None]
                
                self.cs.callproc(proc_name, proc_args)
                self.cn.commit()
                
                return ["200", book_name, rented_on, rent_days, fine, user_name, user_email, due_fees, total_fees]
            else:
                fine = None
                rent_days = None
                book_name = None
                rented_on = None
                user_name = None
                user_email = None
                due_fees = None
                total_fees = None
                return ["500", book_name, rented_on, rent_days, fine, user_name, user_email, due_fees, total_fees]
        except Exception:
                fine = None
                rent_days = None
                book_name = None
                rented_on = None
                user_name = None
                user_email = None
                due_fees = None
                total_fine = None
                return ["500", book_name, rented_on, rent_days, fine, user_name, user_email, due_fees, total_fees]
    
    # this method takes user id and submit the fees
    def submit_fees(self, app_user_id, user_id, fees):
        try:
            sql_query = f"SELECT first_name, last_name, email, fees FROM user WHERE user_id={user_id} AND status=1 AND fees>={fees};"
            self.cs.execute(sql_query)
            query_result2 = self.cs.fetchone()
                
            user_name = f"{query_result2[0]} {query_result2[1]}"
            user_email = query_result2[2]
            due_fees = query_result2[3]
            
            net_remaining_fees = (due_fees - fees)
            
            proc_name = "sp_edit_user"
            proc_args = [0,
                        app_user_id,
                        user_id,
                        None,
                        None,
                        None,
                        None,
                        None,
                        net_remaining_fees,
                        None]
            self.cs.callproc(proc_name, proc_args)
            self.cn.commit()
            return ["200", user_name, user_email, due_fees, net_remaining_fees]
        except Exception:
            user_name = None
            user_email = None
            due_fees = None
            net_remaining_fees = None
            return ["500", user_name, user_email, due_fees, net_remaining_fees]
    
    # same method will be used for - 4, 5, 6
    # get all books, get rented books, get rentable books
    def get_all_books(self,
                      column_names='*',
                      table_name="book",
                      where_clause='1=1',
                      no_of_rows=10,
                      all=True,
                      rows=False):
        try:       
            self.cs.execute(f"SELECT {column_names} FROM {table_name} WHERE status=1 AND {where_clause}")
            if (all == True):
                record_all_list = self.cs.fetchall()
                return ["200", record_all_list]
            elif (all == False):  
                record_n_list = self.cs.fetchmany(no_of_rows)
                return ["200", record_n_list]
        except Exception:
            record_all_list = None
            return ["500", record_all_list]
    
    # 7 - Upload new book
    def upload_book(self, book_detail_list):
        try:
            proc_name = "sp_create_book"
            proc_args = [0,
                        book_detail_list[1],
                        book_detail_list[2],
                        book_detail_list[3],
                        book_detail_list[4],
                        book_detail_list[5],
                        book_detail_list[6],
                        None,
                        0]
            
            created_book = self.cs.callproc(proc_name, proc_args)
            self.cn.commit()
            return ["200", created_book]
        except Exception:
            created_book = None
            return ["500", created_book]
    
    # 8 edit a book
    def edit_book(self, book_detail_list):
        try:
            sql_query = f"SELECT book_id FROM book WHERE status=1 AND book_id={book_detail_list[2]};"
            self.cs.execute(sql_query)
            query_result1 = self.cs.fetchone()
            
            if(query_result1 != None):
                proc_name = "sp_edit_book"
                proc_args = [book_detail_list[0],
                            book_detail_list[1],
                            book_detail_list[2],
                            book_detail_list[3],
                            book_detail_list[4],
                            book_detail_list[5],
                            book_detail_list[6],
                            book_detail_list[7],
                            book_detail_list[8],
                            book_detail_list[9],
                            book_detail_list[10],
                            book_detail_list[11]]
                
                self.cs.callproc(proc_name, proc_args)
                self.cn.commit()
                return "200"
            else:
                return "500"
        except Exception:
            return "500"
        
    # 9 - delete a book
    def delete_book(self, app_user_id, book_id):
        try:
            sql_query = f"SELECT book_id FROM book WHERE status=1 AND is_rented=0 AND book_id={book_id};"
            self.cs.execute(sql_query)
            query_result1 = self.cs.fetchone()
            
            if(query_result1 != None):
                datetime_reset = "0000-00-00 00:00:00"
                proc_name = "sp_edit_book"
                proc_args = [0,
                            app_user_id,
                            book_id,
                            self.super_admin_id,
                            None,
                            None,
                            None,
                            None,
                            None,
                            0,
                            datetime_reset,
                            0]
                
                self.cs.callproc(proc_name, proc_args)
                self.cn.commit()
                return "200"
            else:
                return "500"
        except Exception:
            return "500"
        
    # 10 - get all users with role
    def get_user_with_role(self, user_id=None):
        try:
            proc_name = "sp_get_user_with_role"
            proc_args = [0, None]
            
            self.cs.callproc(proc_name, proc_args)
            all_users_with_role = [r.fetchall() for r in self.cs.stored_results()]
            return ["200", all_users_with_role]
        except Exception:
            all_users_with_role = None
            return ["500", all_users_with_role]
    
    # 11 - update an user
    def edit_user(self, edit_user_details):
        try:
            sql_query = f"SELECT user_id FROM user WHERE user_id={edit_user_details[2]} AND status=1;"
            self.cs.execute(sql_query)
            query_result2 = self.cs.fetchone()
            
            if(query_result2 != None):   
                proc_name = "sp_edit_user"
                proc_args = edit_user_details
                self.cs.callproc(proc_name, proc_args)
                self.cn.commit()
                return "200"
            else:
                return "500"
        except Exception:
            return "500"
    
    # 12 - delete an user
    def delete_user(self, edit_user_details):
        try:
            sql_query = f"SELECT user_id FROM user WHERE user_id={edit_user_details[2]} AND status=1;"
            self.cs.execute(sql_query)
            query_result2 = self.cs.fetchone()
            
            if(query_result2 != None):       
                proc_name = "sp_edit_user"
                proc_args = edit_user_details
                self.cs.callproc(proc_name, proc_args)
                self.cn.commit()
                return "200"
            else:
                return "500"
        except Exception:
            return "500"
            
    # 3 - get single user by id
    def get_single_user_with_role(self, user_id):
        try:
            proc_name = "sp_get_single_user_with_role"
            proc_args = [0, user_id]
            
            self.cs.callproc(proc_name, proc_args)
            all_users_with_role = [r.fetchone() for r in self.cs.stored_results()]
            return ["200", all_users_with_role]
        except Exception:
            all_users_with_role = None
            return ["500", all_users_with_role]